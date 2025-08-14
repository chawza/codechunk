import os
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction, EmbeddingFunction
from pydantic.fields import Field
from pydantic.v1.main import BaseModel

from codechunk.chunker import Chunker, FileChunk
from codechunk.core import Repository
from codechunk.utils import get_text_and_code_file_regex, logger, get_skip_patterns


class FileIndexResult(BaseModel):
    filename: str
    chunk_count: int

class IndexSummary(BaseModel):
    file_count: int = 0
    chunk_count: int = 0

class Indexer:
    def __init__(self, db_name: str, batch_size: int = 30) -> None:
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(db_name, embedding_function=self.get_embedding_function())
        self.chunker = Chunker(chunk_size=30)
        self.batch_size = batch_size

    def get_embedding_function(self) -> EmbeddingFunction | None:
        return None

    def index(self, repo: Repository) -> IndexSummary:
        summary = IndexSummary()
        pattern = get_text_and_code_file_regex()
        skip_pattern = get_skip_patterns()
        chunks: list[FileChunk] = []

        for root, _, files in os.walk(repo.cache_dir_path):
            for file in files:
                if '.git' in root:
                    continue

                if not pattern.search(file) or skip_pattern.search(file):
                    continue

                summary.file_count += 1
                absoulute_path = os.path.join(root, file)
                relative_path = absoulute_path.replace(repo.cache_dir_path, '').lstrip('/')
                logger.debug(f'Indexing {relative_path}')

                for chunk in self.chunker.chunk_file(absoulute_path, relative_path):
                    chunks.append(chunk)

                    if len(chunks) >= self.batch_size:
                        self._index_chunks(chunks)
                        chunks = []
                        summary.chunk_count += self.batch_size

        if chunks:
            self._index_chunks(chunks)
            summary.chunk_count += len(chunks)
            chunks = []

        return summary

    def _index_chunks(self, chunks: list[FileChunk]):
        logger.debug(f'Indexing {len(chunks)} chunks')
        upsert_ids = [chunk.document_id for chunk in chunks]
        upsert_documents = [chunk.content for chunk in chunks]
        self.collection.upsert(ids=upsert_ids, documents=upsert_documents)

class OpenAIIndexer(Indexer):
    def get_embedding_function(self) -> OpenAIEmbeddingFunction | None:
        return OpenAIEmbeddingFunction(
            api_key=os.environ['INDEX_API_KEY'],
            api_base=os.environ['INDEX_API_BASE'],
            model_name=os.environ['INDEX_MODEL_NAME']
        )
