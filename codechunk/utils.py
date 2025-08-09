import logging
import sys

logger = logging.getLogger('codechunk')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.addHandler(logging.FileHandler('.codechunk.log'))
logger.setLevel(logging.DEBUG)
