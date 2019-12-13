"""
Utility functions to be used across different ComRAD modules.
"""
import os
import logging
from types import ModuleType
from typing import Optional
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
