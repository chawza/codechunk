from collections import defaultdict
import pickle
import os
import chromadb
import textwrap
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction, EmbeddingFunction
from pydantic import BaseModel

from codechunk.chunker import Chunker, FileChunk
from codechunk.core import Repository
from codechunk.utils import get_text_and_code_file_regex, logger


class FileIndexResult(BaseModel):
    filename: str
    chunk_count: int

class IndexSummary(BaseModel):
    files: dict[str, int]
    total_chunk: int
    total_files: int

    def to_csv(self, buffer) -> None:
        import csv
        writer = csv.writer(buffer)
        writer.writerow(['filename', 'chunks count'])
        for filename, chunk_count in self.files.items():
            writer.writerow([filename, str(chunk_count)])
        writer.writerow(['file count', str(self.total_files)])
        writer.writerow(['chunk count', str(self.total_chunk)])

class IndexCache(BaseModel):
    # TODO: append file, rather thank rewrite
    name:str
    state: set[str]  # filename to document_id(d)

    @property
    def cache_path(self) -> str:
        return f'./{self.name}_cache.pickle'

    def save(self):
        with open(self.cache_path, 'wb') as buffer:
            pickle.dump(self.state, buffer)

    def load(self):
        with open(self.cache_path, 'rb') as buffer:
            self.state = pickle.load(buffer)
            if not isinstance(self.state, set):
                raise TypeError(self.state)

    def setup(self):
        if os.path.exists(self.cache_path):
            self.load()
            logger.info(f'loaded {len(self.state)} (chunks) cached chunk from {self.cache_path}')


class Indexer:
    def __init__(self, db_name: str, batch_size: int = 30) -> None:
        self.client = chromadb.PersistentClient(path=f'{db_name}.chroma')
        self.collection = self.client.get_or_create_collection(db_name, embedding_function=self.get_embedding_function())
        self.chunker = Chunker(chunk_size=30)
        self.batch_size = batch_size

        self.cache = IndexCache(name=db_name, state=set())
        self.cache.setup()

    def get_embedding_function(self) -> EmbeddingFunction | None:
        return None

    def index(self, repo: Repository) -> IndexSummary:
        pattern = get_text_and_code_file_regex()
        chunks: list[FileChunk] = []

        for root, _, files in os.walk(repo.cache_dir_path):
            for file in files:
                if '.git' in root:
                    continue

                if not pattern.search(file):
                    continue

                absoulute_path = os.path.join(root, file)
                relative_path = absoulute_path.replace(repo.cache_dir_path, '').lstrip('/')

                for chunk in self.chunker.chunk_file(absoulute_path, relative_path):
                    if chunk.document_id in self.cache.state:
                        continue

                    chunks.append(chunk)

                    if len(chunks) >= self.batch_size:
                        self._index_chunks(chunks)
                        chunks = []

        if chunks:
            self._index_chunks(chunks)
            chunks = []

        filename_to_count_mapping = defaultdict(int)
        total_chunks = 0
        filenames = set()

        for document_id in self.cache.state:
            filename = document_id.split(':')[0]
            total_chunks += 1
            filename_to_count_mapping[filename] += 1
            filenames.add(filename)

        return IndexSummary(
            total_files=len(filenames),
            total_chunk=total_chunks,
            files=filename_to_count_mapping
        )

    def _index_chunks(self, chunks: list[FileChunk]):
        logger.debug(f'Indexing {len(chunks)} chunks')
        upsert_ids = [chunk.document_id for chunk in chunks]
        upsert_documents = [chunk.content for chunk in chunks]
        upsert_metadatas = [chunk.metadata_dict for chunk in chunks]
        self.collection.upsert(ids=upsert_ids, documents=upsert_documents, metadatas=upsert_metadatas)  # type: ignore[reportargumenttype]

        for chunk in chunks:
            self.cache.state.add(chunk.document_id)

        self.cache.save()
        logger.debug(f'Saving cache {self.cache.cache_path} {len(self.cache.state)} (chunks)')

class OpenAIIndexer(Indexer):
    def get_embedding_function(self) -> OpenAIEmbeddingFunction | None:
        return OpenAIEmbeddingFunction(
            api_key=os.environ['INDEX_API_KEY'],
            api_base=os.environ['INDEX_API_BASE'],
            model_name=os.environ['INDEX_MODEL_NAME']
        )

def generate_queries(query: str, number: int = 3) -> list[str]:
    from openai import OpenAI
    client = OpenAI(base_url=os.environ['OPENAI_BASE_URL'], api_key=os.environ['OPENAI_API_KEY'])

    class QueryFormat(BaseModel):
        queries: list[str]

    response = client.chat.completions.parse(
        model=os.environ['OPENAI_MODEL'],
        messages=[
            {
                'role': "system",
                'content': textwrap.dedent("""\
                    You are a Retrieval Augmented Generation (RAG) tool that is part of chatbot.
                    the chatbot retrieves chunks of documents about coding repository or project.
                    your task is to make more RAG queries from given user's query.
                    each query is an expansion points that elaborate more user intention.
                    the output is a structured json from given schema.""")
            },
            {
                "role": "user",
                "content": f"Expand this query into {number} points\n<query>{query}<query/>"
            }
        ],
        response_format=QueryFormat,
    )
    parsed_output = response.choices[0].message.parsed
    if not parsed_output:
        raise ValueError(f'Invalid Structured Response: {parsed_output}')
    return parsed_output.queries
