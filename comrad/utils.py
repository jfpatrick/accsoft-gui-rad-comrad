"""
Utility functions to be used across different ComRAD modules.
"""
import os
import logging
from types import ModuleType
from typing import Optional, Dict
from qtpy.QtGui import QIcon, QPixmap


logger = logging.getLogger(__name__)


def icon(name: str, file_path: Optional[str] = None, module_path: Optional[ModuleType] = None) -> QIcon:
    """
    Loads the icon with the given name, provided that the file is located relative to the called,
    inside ./icons directory and is of ICO extension.

    Args:
        name: basename for the *.ico file.
        file_path: location of the caller file.

    Returns:
        Icon object.
    """
    if file_path is not None:
        storage_dir = os.path.abspath(os.path.dirname(file_path))
    elif module_path is not None:
        import inspect
        storage_dir = os.path.abspath(os.path.dirname(inspect.getfile(module_path)))
    else:
        raise ValueError(f'Neither file_path nor module_path are specified')

    icon_path = os.path.join(storage_dir, 'icons', f'{name}.ico')

    if not os.path.isfile(icon_path):
        logger.warning(f'Warning: Icon "{name}" cannot be found at {str(icon_path)}')
    pixmap = QPixmap(icon_path)
    return QIcon(pixmap)


def install_logger_level(level: Optional[str]):
    """Sets the root logger level according to the command line parameters.

    Args:
        level: Name of the logging level, e.g. DEBUG or INFO.
    """
    if level:
        import logging
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


ccda_map: Dict[str, str] = {
    'PRO': 'https://ccda.cern.ch:8900/api/',
    'PRO2': 'https://ccda.cern.ch:8901/api/',
    'TEST': 'https://ccda-test.cern.ch:8902/api/',
    'TEST2': 'https://ccda-test.cern.ch:8903/api/',
    'INT': 'https://ccda-int.cern.ch:8904/api/',
    'INT2': 'https://ccda-int.cern.ch:8905/api/',
    'DEV': 'https://ccda-dev.cern.ch:8906/api/',
    'DEV2': 'https://ccda-dev.cern.ch:8907/api/',
}
