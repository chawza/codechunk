
from unittest import TestCase
from math import ceil

from codechunk.chunker import Chunker


class ChunkerTestCase(TestCase):
    def test_1(self) -> None:
        chunker = Chunker(chunk_size=5)

        sample_file_path = 'fixtures/lorem.txt'

        with open(sample_file_path, 'r') as file:
            file_line_counts = len(file.readlines())

        total_chunks = ceil(file_line_counts / 5)

        chunks = list(chunker.chunk_file(sample_file_path))

        self.assertEqual(total_chunks, len(chunks))

        for chunk in chunks:
            self.assertLessEqual(chunk.end_line - chunk.start_line, 5 - 1)
            chunk_line_numbers = len(chunk.content.splitlines())
            self.assertLessEqual(chunk_line_numbers, 5, f'{chunk_line_numbers=}\n{chunk}')
