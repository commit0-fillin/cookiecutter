"""Module for setting up logging."""
import logging
import sys
LOG_LEVELS = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR, 'CRITICAL': logging.CRITICAL}
LOG_FORMATS = {'DEBUG': '%(levelname)s %(name)s: %(message)s', 'INFO': '%(levelname)s: %(message)s'}

def configure_logger(stream_level='DEBUG', debug_file=None):
    """Configure logging for cookiecutter.

    Set up logging to stdout with given level. If ``debug_file`` is given set
    up logging to file with DEBUG level.
    """
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVELS.get(stream_level, logging.DEBUG))
    console_formatter = logging.Formatter(LOG_FORMATS.get(stream_level, LOG_FORMATS['DEBUG']))
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # If debug_file is provided, create a file handler
    if debug_file:
        file_handler = logging.FileHandler(debug_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMATS['DEBUG'])
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
