import chromadb
import os
from pydantic.main import BaseModel

from codechunk.chunker import Chunker, FileChunk
from codechunk.utils import logger


def parse_github_repo_url(url) -> tuple[str, str] | None:
    import re
    pattern = r"^(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)(?:(?:\.git)|(?:\/.*))?$"

    match = re.match(pattern, url)

    if match:
        owner = match.group(1)
        repo_name = match.group(2)
        return owner, repo_name
    else:
        return None

class Repository(BaseModel):
    owner: str
    name: str

    @classmethod
    def from_url(cls, url: str) -> 'Repository | None':
        result = parse_github_repo_url(url)

        if result:
            return Repository(
                owner=result[0],
                name=result[1]
            )

        return None

    @property
    def cache_dir_path(self) -> str:
        return os.path.join(os.environ['HOME'], '.cache', 'codechunk', 'projects', self.owner, self.name)

    def cache_dir_exists(self) -> bool:
        return os.path.exists(self.cache_dir_path)

    def setup_cache_dir(self) -> str:
        if not os.path.exists(self.cache_dir_path):
            logger.debug(f'setup cache dir for in {self.cache_dir_path}')
            os.makedirs(self.cache_dir_path, exist_ok=True)


def clone_project(repo: Repository, github_token: str | None = None, force: bool = False):
    import subprocess

    if repo.cache_dir_exists():
        if force:
            pass # TODO: delete cache and reclone
        else:
            logger.debug(f'Trying to clone cache dir to {repo.cache_dir_path} but already exists')
            return

    if github_token:
        auth_str = f'{github_token}@'
    else:
        auth_str = ''

    command = [
        'git',
        'clone',
        f'https://{auth_str}github.com/{repo.owner}/{repo.name}.git',
        repo.cache_dir_path,
    ]

    logger.info(f'Cloning repo to {repo.cache_dir_path}')
    logger.debug(f'Execute: {command}')

    subprocess.run(command, capture_output=True, text=True, check=True)

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

        result = FileIndexResult(filename, chunk_count=0)
        chunks: list[FileChunk] = []

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
