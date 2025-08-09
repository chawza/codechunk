import logging
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
