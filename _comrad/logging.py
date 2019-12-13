import logging
from typing import Optional
import colorlog


def _setup_logging():
    # Setup logging with colors
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s[%(levelname)s]: %(name)s => %(reset)s%(message)s',
        reset=True,
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    logging.basicConfig(handlers=[handler])


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


_LOGGING_SETUP: bool = False
if not _LOGGING_SETUP:
    _LOGGING_SETUP = True
    _setup_logging()
