"""Simple wrapper that makes a logger which writes to a queue
and makes a listener on that queue to write out from
    multiple processes. Requires an owner to manage it
    but reduces multiprocesisng weirdness from logging
"""

import datetime
import logging.handlers
import multiprocessing as mp
from typing import Final

from pyantz.infrastructure.config.base import LoggingConfig

ANTZ_LOG_ROOT_NAME: Final[str] = "antz"


def get_listener(
    logging_config: LoggingConfig,
) -> tuple[mp.Queue, logging.handlers.QueueListener]:
    """Get listener, which will handle messages published to a queue
        and write them out to handlers based on configuration

    Args:
        logging_config (LoggingConfig): configuration of this logging module

    Returns:
        tuple[mp.Queue, logging.handlers.QueueListener]:
            1. the queue for queue handlers
            2. listener handle for stopping in the future
    """

    queue: mp.Queue = mp.Queue()
    handlers = _get_handlers(logging_config)
    return queue, logging.handlers.QueueListener(queue, *handlers)


def _get_handlers(logging_config: LoggingConfig) -> list[logging.Handler]:
    """Return handlers for the given configuration"""

    # FUTURE: improve handlers based on configuration
    return [_get_file_handler(logging_config)]


def _get_file_handler(
    _logging_config: LoggingConfig,
) -> logging.handlers.RotatingFileHandler:
    """For handlers for local file storage, return the file handler

    Args:
        logging_config (LoggingConfig): configuration of the logger

    Returns (RotatingFileHandler): file handler for local runner config
    """

    file_name = f"LOG_{datetime.datetime.now()}.log"
    return logging.handlers.RotatingFileHandler(file_name, delay=True)
