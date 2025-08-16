import logging
import re
import sys
import os

IS_TEST = os.environ.get('TEST', '').lower() == 'true' or 'unittest' in sys.argv

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO if not IS_TEST else logging.NOTSET)
file_handler = logging.FileHandler('.codechunk.log')
file_handler.setLevel(logging.DEBUG if not IS_TEST else logging.NOTSET)

logger = logging.getLogger('codechunk')
logger.addHandler(stream_handler)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

# Common text file extensions
TEXT_EXTENSIONS = [
    r'txt', r'md', r'markdown', r'log', r'nfo', r'rtf', r'csv', r'tsv',
    r'json', r'xml', r'yaml', r'y(a?)ml', r'toml', r'ini', r'cfg',
    r'conf', r'config', r'env', r'text', r'asciidoc', r'adoc', r'rst',
    r'htm', r'html', r'css', r'js', r'jsx', r'ts', r'tsx', r'php',
    r'sh', r'bash', r'zsh', r'csh', r'bat', r'ps1', r'vbs', r'vb'
]

# Common code file extensions
CODE_EXTENSIONS = [
    r'py', r'java', r'c', r'cpp', r'h', r'hpp', r'go', r'rs', r'swift',
    r'kt', r'kts', r'rb', r'pl', r'R', r'php', r'cs', r'm', r'f', r'for',
    r'cob', r'clj', r'cljs', r'scala', r'sc', r'groovy', r'gvy', r'gd',
    r'ex', r'exs', r'hs', r'lhs', r'ml', r'mli', r'fs', r'fsi', r'lisp',
    r'scm', r'ss', r'lua', r'nim', r'd', r'zig', r'v', r'vhd', r'vhdl',
    r'sv', r'svh', r'awk', r'sed', r'perl', r'sql', r'graphql', r'gql',
    r'dart', r'svelte', r'vue', r'astro', r'sol' # Solidity
]

# Combine all desired text and code extensions using '|' for OR
# Using a set for efficiency and unique elements before joining
all_matched_extensions = sorted(list(set(TEXT_EXTENSIONS + CODE_EXTENSIONS)))
matched_pattern = r'\.(' + '|'.join(all_matched_extensions) + r')$'


# Function to compile the positive regex
def get_text_and_code_file_regex():
    """
    Returns a compiled regex pattern that matches common file extensions
    associated with human-readable text files and code files.

    This regex *only* considers the file extension. It does not inspect
    file content for binary vs. text status.
    """
    # Case-insensitive matching for extensions
    return re.compile(matched_pattern, re.IGNORECASE)
