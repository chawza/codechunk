import sys
import typer

from codechunk.core import Repository, clone_project
from codechunk.logging import logger

app = typer.Typer()
@app.command()
def setup(project_url: str):

    repo = Repository.from_url(project_url)

    if not repo:
        logger.info(f'Repository with url {project_url} not found')
        return

    github_token = typer.prompt('Github Personal Access Token')

    if not repo.cache_dir_exists():
        logger.info(f'Setup repository')
        clone_project(repo, github_token=github_token)

if __name__ == '__main__':
    app()
