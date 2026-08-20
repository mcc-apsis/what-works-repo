"""Set up logging."""

import os
import sys

from loguru import logger

_level = os.environ.get("LOG_LEVEL", "INFO")

logger.remove()
logger.add(sys.stderr, level=_level)
