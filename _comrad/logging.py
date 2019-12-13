import logging
from typing import Optional


def install_logger_level(level: Optional[str]):
    """Sets the root logger level according to the command line parameters.

    Args:
        level: Name of the logging level, e.g. DEBUG or INFO.
    """
    logging.basicConfig()
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
        logger.debug(f'DEBUG logging is enabled')
