from collections import defaultdict
import pickle
import os
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction, EmbeddingFunction
from pydantic.fields import Field
from pydantic.v1.main import BaseModel

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

class IndexCache(BaseModel):
    # TODO: append file, rather thank rewrite
    name:str
    state: dict[str, list[str]]  # filename to document_id(d)

    @property
    def cache_path(self) -> str:
        return f'./{self.name}_cache.pickle'

    def save(self):
        with open(self.cache_path, 'wb') as buffer:
            pickle.dump(self.state, buffer)

    def load(self):
        with open(self.cache_path, 'rb') as buffer:
            self.state = pickle.load(buffer)
            if not isinstance(self.state, dict):
                raise TypeError(self.state)

    def setup(self):
        if os.path.exists(self.cache_path):
            self.load()
            logger.info(f'loaded {len(self.state.keys())} (chunks) cached chunk from {self.cache_path}')


class Indexer:
    def __init__(self, db_name: str, batch_size: int = 30) -> None:
        self.client = chromadb.PersistentClient(path=f'{db_name}.chroma')
        self.collection = self.client.get_or_create_collection(db_name, embedding_function=self.get_embedding_function())
        self.chunker = Chunker(chunk_size=30)
        self.batch_size = batch_size

        self.cache = IndexCache(name=db_name, state={})
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

        for filename, ids in self.cache.state.items():
            document_count = len(ids)
            total_chunks += document_count
            filename_to_count_mapping[filename] += document_count

        return IndexSummary(
            total_files=len(self.cache.state.keys()),
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
            if chunk.filename not in self.cache.state:
                self.cache.state[chunk.filename] = []
            self.cache.state[chunk.filename].append(chunk.document_id)

        self.cache.save()
        logger.debug(f'Saving cache {self.cache.cache_path} {len(self.cache.state.keys())} (chunks)')

class OpenAIIndexer(Indexer):
    def get_embedding_function(self) -> OpenAIEmbeddingFunction | None:
        return OpenAIEmbeddingFunction(
            api_key=os.environ['INDEX_API_KEY'],
            api_base=os.environ['INDEX_API_BASE'],
            model_name=os.environ['INDEX_MODEL_NAME']
        )
