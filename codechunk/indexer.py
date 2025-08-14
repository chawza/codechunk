import os
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction, EmbeddingFunction
from pydantic.v1.main import BaseModel

from codechunk.chunker import Chunker, FileChunk
from codechunk.utils import logger


class FileIndexResult(BaseModel):
    filename: str
    chunk_count: int

class Indexer:
    def __init__(self, db_name: str, batch_size: int = 30) -> None:
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(db_name, embedding_function=self.get_embedding_function())
        self.chunker = Chunker(chunk_size=30)
        self.batch_size = batch_size

    def get_embedding_function(self) -> EmbeddingFunction | None:
        return None

    def index_file(self, filepath: str, filename: str):
        result = FileIndexResult(filename=filename, chunk_count=0)

        chunks = []

        for chunk in self.chunker.chunk_file(filepath, filename):
            chunks.append(chunk)
            result.chunk_count += 1

            if len(chunks) >= self.batch_size:
                self._index_chunks(chunks)
                chunks = []

        if chunks:
            self._index_chunks(chunks)
            chunks = []

        return result

    def _index_chunks(self, chunks: list[FileChunk]):
        logger.debug(f'Indexing {len(chunks)} chunks')
        upsert_ids = [chunk.document_id for chunk in chunks]
        upsert_documents = [chunk.content for chunk in chunks]
        self.collection.upsert(ids=upsert_ids, documents=upsert_documents)

class OpenAIIndexer(Indexer):
    def get_embedding_function(self) -> EmbeddingFunction | None:
        return OpenAIEmbeddingFunction(
            api_key=os.environ['INDEX_API_KEY'],
            api_base=os.environ['INDEX_API_BASE'],
            model_name=os.environ['INDEX_MODEL_NAME']
        )
