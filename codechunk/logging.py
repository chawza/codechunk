import logging
import sys

logger = logging.getLogger('codechunk')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)
