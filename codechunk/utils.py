import logging
import sys

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
file_handler = logging.FileHandler('.codechunk.log')
file_handler.setLevel(logging.DEBUG)

logger = logging.getLogger('codechunk')
logger.addHandler(stream_handler)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)
