import os
import logging
from typing import Optional
from qtpy.QtGui import QIcon, QPixmap


logger = logging.getLogger(__name__)


def icon(name: str, file_path: Optional[str] = None) -> QIcon:
    """
    Loads the icon with the given name, provided that the file is located in comrad/icons or relative to the file_path,
    and is always inside ./icons directory and is of ICO extension.

    Args:
        name: basename for the *.ico file.
        file_path: location of the caller file.

    Returns:
        Icon object.
    """
    file_name = f'{name}.ico'
    if not file_path:
        file_path = __file__
        components = [file_name]
    else:
        components = ['icons', file_name]

    storage_dir = os.path.abspath(os.path.dirname(file_path))
    icon_path = os.path.join(storage_dir, *components)

    if not os.path.isfile(icon_path):
        logger.warning(f'Warning: Icon "{name}" cannot be found at {str(icon_path)}')
    pixmap = QPixmap(icon_path)
    return QIcon(pixmap)
