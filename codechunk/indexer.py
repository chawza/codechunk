import chromadb
from pydantic.v1.main import BaseModel

from codechunk.chunker import Chunker, FileChunk
from codechunk.utils import logger


class FileIndexResult(BaseModel):
    filename: str
    chunk_count: int

class Indexer:
    def __init__(self, db_name: str = None, batch_size: int = 30) -> None:
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(db_name)
        self.chunker = Chunker(30)
        self.batch_size = batch_size

    def index_file(self, filename: str):
        logger.debug(f'Indexing file {filename}')

        result = FileIndexResult(filename=filename, chunk_count=0)


        for chunk in self.chunker.chunk_file(file_path=filename):
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
