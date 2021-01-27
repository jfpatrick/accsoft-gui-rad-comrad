import sys
import logging
from typing import Optional
from colorlog import StreamHandler, ColoredFormatter


# Definition where is the level that decides which logs go to stdout and which to stderr
_ERROR_THRESHOLD = logging.WARNING


def _setup_logging():
    # Setup logging with colors
    formatter = ColoredFormatter(
        '%(log_color)s[%(levelname)s]: %(name)s => %(reset)s%(message)s',
        reset=True,
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
    )

    # Prevent error logs to go to stdout, as they will be redirected to stderr
    class StdoutFilter(logging.Filter):

        def filter(self, record: logging.LogRecord):
            return record.levelno < _ERROR_THRESHOLD

    stdout_handler = StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(StdoutFilter())

    stderr_handler = StreamHandler(stream=sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(_ERROR_THRESHOLD)
    logging.basicConfig(handlers=[stdout_handler, stderr_handler])

    # Initialize standard loggers, that are picked up by CLogConsole by default
    logging.getLogger('comrad')  # This will be parent for all comrad.* loggers
    logging.getLogger('pydm')  # This will be parent for all pydm.* loggers


def install_logger_level(level: Optional[str]):
    """Sets the root logger level according to the command line parameters.

    Args:
        level: Name of the logging level, e.g. DEBUG or INFO.
    """
    if level:
        level_name: str = level.upper()
        level_idx: Optional[int]
        logger = logging.getLogger('')
        try:
            level_idx = getattr(logging, level_name)
        except AttributeError as ex:
            logger.exception(f'Invalid logging level specified ("{level_name}"): {str(ex)}')
            level_idx = None

        if level_idx:
            # Redefine the level of the root logger
            logger.setLevel(level_idx)
    else:
        # This covers both NOTSET (=0), and None (not passed in arguments)

        # Hide PyDM INFO messages that are impossible to silence (only if no log level has been selected by the user)
        logging.getLogger('pydm').setLevel(logging.WARNING)

        # Install it to INFO for the rest of things
        install_logger_level('INFO')


_LOGGING_SETUP: bool = False
if not _LOGGING_SETUP:
    _LOGGING_SETUP = True
    _setup_logging()
