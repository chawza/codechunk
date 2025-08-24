import datetime
import os
from pathlib import Path
from pydantic import ConfigDict, BaseModel
import typer
from datetime import datetime

from codechunk.chunker import FileChunk
from codechunk.core import Repository, clone_project, get_all_projects, get_current_commit_id
from codechunk.indexer import OpenAIIndexer, generate_queries
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

class OutputResult(BaseModel):
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
        logger.info('try `docgen index <repo url>` first')
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

    expanded_queries = generate_queries(query, number=5)
    logger.info(f'Generated {len(expanded_queries)} queries')

    output_result = OutputResult(created=int(datetime.now().timestamp()), chunks=[], repo=project_name, hash=get_current_commit_id(repo))
    inserted_doc_ids = set()

    for _query in expanded_queries:
        result = indexer.collection.query(query_texts=[_query,], n_results=n)
        for id, document, distance in zip(result['ids'][0], result['documents'][0], result['distances'][0]):
            chunk = FileChunk.from_document_id(id, document)

            if chunk.document_id in inserted_doc_ids:
                continue

            output_result.chunks.append(
                ChunkDetail(
                    **chunk.model_dump(),
                    distance=distance
                )
            )

            inserted_doc_ids.add(chunk.document_id)


    logger.info(f'{len(output_result.chunks)} queries chunks ')

    if str(output).endswith('.json'):
        with open(output, 'w') as file:
            file.write(output_result.model_dump_json(indent=2))
            logger.info(f'Result in "{file.name}"')

    elif str(output).endswith('.txt') or str(output).endswith('.md'):
        with open(output, 'w') as file:
            for chunk in output_result.chunks:
                file.writelines([
                    f'# start {chunk.filename} start:{chunk.start_line} end:{chunk.end_line}\n',
                    chunk.content.rstrip('\n') + '\n',
                    f'# end {chunk.filename} start:{chunk.start_line} end:{chunk.end_line}\n',

                ])
            logger.info(f'Result in "{file.name}"')
    else:
        raise NotImplementedError(f'Not supperted type output {output}')


if __name__ == '__main__':
    app()
