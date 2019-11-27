"""
Utility functions to be used across different ComRAD modules.
"""
import os
from types import ModuleType
from typing import Optional, Dict
from qtpy.QtGui import QIcon, QPixmap


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
        print(f'Warning: Icon "{name}" cannot be found at {str(icon_path)}')
    pixmap = QPixmap(icon_path)
    return QIcon(pixmap)


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