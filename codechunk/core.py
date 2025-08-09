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

    def setup_cache_dir(self) -> None:
        if not os.path.exists(self.cache_dir_path):
            logger.debug(f'setup cache dir for in {self.cache_dir_path}')
            os.makedirs(self.cache_dir_path, exist_ok=True)


def clone_project(repo: Repository, github_token: str | None = None, force: bool = False):
    import subprocess

    if repo.cache_dir_exists():
        if force:
            pass # TODO: delete cache and reclone
        else:
            logger.warning(f'Trying to clone cache dir to {repo.cache_dir_path} but already exists')
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
