from dataclasses import dataclass, Field
from typing import Generator

from pydantic import FilePath

@dataclass
class FileChunk:
    filename: str
    start_line: int
    end_line: int
    content: str


@dataclass
class Chunker:
    chunk_size: int

    def chunk_file(self, file_path: str) -> Generator[FileChunk, None, None]:
        with open(file_path, 'r') as file:
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
                        filename=file_path,
                        start_line=last_first_line,
                        end_line=current_line
                    )
                    last_first_line = None
                    chunk_lines = []


            if chunk_lines:
                yield FileChunk(
                    content='\n'.join(chunk_lines),
                    filename=file_path,
                    start_line=last_first_line,
                    end_line=current_line
                )
