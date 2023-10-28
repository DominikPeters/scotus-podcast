from get_scotus_website import get_from_scotus_website
from get_oyez import get_from_oyez
from upload_podcast import build_podcast

import sys
import logging

# Create a logger object
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# log to stdout
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

try:
    get_from_scotus_website()
    get_from_oyez()
    build_podcast()
except Exception as e:
    logging.exception(e)
    raise e