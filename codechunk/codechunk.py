import os
import typer

from codechunk.core import Repository, clone_project, get_current_commit_id
from codechunk.indexer import OpenAIIndexer
from codechunk.utils import logger

app = typer.Typer()

@app.command()
def index(project_url: str):
    repo = Repository.from_url(project_url)

    if not repo:
        logger.info(f'Repository with url {project_url} not found')
        return

    github_token = os.environ.get("GITHUB_TOKEN") or typer.prompt('Github Personal Access Token')

    if not repo.cache_dir_exists():
        logger.info(f'Setup repository')
        clone_project(repo, github_token=github_token)

    logger.debug(f'Repo "{repo.name}" cache director is in {repo.cache_dir_path}')

    indexer = OpenAIIndexer(f'{repo.name}_{get_current_commit_id(repo)}', batch_size=int(os.environ['INDEX_BATCH_SIZE']))
    summary = indexer.index(repo)

    with open(f'{repo.name}_{get_current_commit_id(repo)}.csv', 'w') as file:
        summary.to_csv(file)
        logger.info(f'summary saved in {file.name}')

@app.command()
def query(project_url: str):
    repo = Repository.from_url(project_url)

    if not repo:
        logger.info(f'Repository with url {project_url} not found')
        return

    indexer = OpenAIIndexer(f'{repo.name}_{get_current_commit_id(repo)}', batch_size=int(os.environ['INDEX_BATCH_SIZE']))

    while True:
        query = typer.prompt('Query')
        if query:
            result = indexer.collection.query(query_texts=[query,], n_results=5)
            for id, document, distance in zip(result['ids'][0], result['documents'][0], result['distances'][0]):
                logger.info(f'Document Id: {id} | distance: {distance:.3f}')
                logger.info(str(document))


if __name__ == '__main__':
    app()
