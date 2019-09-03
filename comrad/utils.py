"""
Utility functions to be used across different ComRAD modules.
"""
import os
from qtpy.QtGui import QIcon, QPixmap


def icon(name: str, file_path: str) -> QIcon:
    """
    Loads the icon with the given name, provided that the file is located relative to the called,
    inside ./icons directory and is of ICO extension.

    Args:
        name: basename for the *.ico file.
        file_path: location of the caller file.

    Returns:
        Icon object.
    """
    curr_dir = os.path.abspath(os.path.dirname(file_path))
    icon_path = os.path.join(curr_dir, 'icons', f'{name}.ico')

    if not os.path.isfile(icon_path):
        print(f'Warning: Icon "{name}" cannot be found at {str(icon_path)}')
    pixmap = QPixmap(icon_path)
    return QIcon(pixmap)