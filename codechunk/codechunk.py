import datetime
import os
from pathlib import Path
from pydantic import ConfigDict, BaseModel
import typer
from datetime import datetime

from codechunk.chunker import FileChunk
from codechunk.core import Repository, clone_project, get_all_projects, get_current_commit_id
from codechunk.indexer import OpenAIIndexer
from codechunk.ui import ProjectSelection
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

class ChunkDetail(FileChunk):
    distance: float

class JSONOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    repo: str  # owner/repo
    hash: str
    created: int
    chunks: list[ChunkDetail]

@app.command()
def query(output: Path = Path('output.json'), n: int = 5):
    project_names = ['/'.join([owner, name]) for owner, name in get_all_projects()]

    if not project_names:
        logger.info('No project indexed')
        return

    project_selection_app = ProjectSelection(project_names)
    project_selection_app.run()
    project_name = project_selection_app.result

    owner, project_name = project_name.split('/')

    repo = Repository(
        owner=owner,
        name=project_name
    )

    indexer = OpenAIIndexer(f'{repo.name}_{get_current_commit_id(repo)}', batch_size=int(os.environ['INDEX_BATCH_SIZE']))

    while True:
        query = typer.prompt('Query')
        if query:
            break

    result = indexer.collection.query(query_texts=[query,], n_results=n)

    output_result = JSONOutput(created=int(datetime.now().timestamp()), chunks=[], repo=project_name, hash=get_current_commit_id(repo))

    for id, document, distance in zip(result['ids'][0], result['documents'][0], result['distances'][0]):
        chunk = FileChunk.from_document_id(id, document)
        output_result.chunks.append(
            ChunkDetail(
                **chunk.model_dump(),
                distance=distance
            )
        )

    with open(output, 'w') as file:
        file.write(output_result.model_dump_json(indent=2))
        logger.info(f'Result in "{file.name}"')


if __name__ == '__main__':
    app()
