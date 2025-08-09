import os
import sys
import typer

from codechunk.core import Repository, clone_project
from codechunk.indexer import Indexer
from codechunk.utils import logger

app = typer.Typer()
@app.command()
def setup(project_url: str):

    repo = Repository.from_url(project_url)

    if not repo:
        logger.info(f'Repository with url {project_url} not found')
        return

    github_token = os.environ.get("GITHUB_TOKEN") or typer.prompt('Github Personal Access Token')

    if not repo.cache_dir_exists():
        logger.info(f'Setup repository')
        clone_project(repo, github_token=github_token)

    logger.debug(f'Repo "{repo.name}" cache director is in {repo.cache_dir_path}')

    indexer = Indexer(repo.name, batch_size=30)
    index_results = repo.index_files(indexer)

    logger.info(f'{'file':<30} | {'chunks':<30}')
    for index_result in index_results:
        filename = index_result.filename.lstrip(repo.cache_dir_path)
        logger.info(f'{filename:<30} | {index_result.chunk_count:>10} chunk(s)')

if __name__ == '__main__':
    app()
