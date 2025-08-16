from dataclasses import dataclass, Field
from typing import Generator
import hashlib

from pydantic import BaseModel

class FileChunk(BaseModel):
    filename: str
    start_line: int
    end_line: int
    content: str
    file_hash: str

    @property
    def document_id(self) -> str:
        return ':'.join([self.filename, str(self.start_line), str(self.end_line), self.file_hash])

    @property
    def metadata_dict(self) -> dict[str, int | str]:
        return self.model_dump(exclude={'content',})


@dataclass
class Chunker:
    chunk_size: int

    def chunk_file(self, filepath: str, filename: str) -> Generator[FileChunk, None, None]:
        with open(filepath, 'r') as file:
            file_hash = hashlib.md5(file.read().encode()).hexdigest()
            file.seek(0)

            chunk_lines: list[str] = []

            last_first_line = None
            current_line = 0

            while line := file.readline():
                current_line += 1
                chunk_lines.append(line.rstrip())

                if last_first_line is None:
                    last_first_line = current_line

                assert current_line >= last_first_line

                if current_line % self.chunk_size == 0:
                    yield FileChunk(
                        content='\n'.join(chunk_lines),
                        filename=filename,
                        start_line=last_first_line,
                        end_line=current_line,
                        file_hash=file_hash,
                    )
                    last_first_line = None
                    chunk_lines = []


            if chunk_lines and last_first_line:
                yield FileChunk(
                    content='\n'.join(chunk_lines),
                    filename=filename,
                    start_line=last_first_line,
                    end_line=current_line,
                    file_hash=file_hash,
                )
