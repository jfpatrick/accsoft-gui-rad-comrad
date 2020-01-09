import logging
from typing import Union, Iterable
from qtpy.QtWidgets import QAction, QMenu
from comrad import CMenuBarPlugin


logger = logging.getLogger('Demo plugin')


class MenuPlugin(CMenuBarPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.bundle-menu'

    def top_level(self) -> Union[str, Iterable[str]]:
        return 'Demo'

    def menu_item(self) -> Union[QAction, QMenu]:
        menu = QMenu('Plugin bundle')
        menu.addAction('Action 1', lambda: logger.info('Action 1 triggered!'))
        menu.addSeparator()
        menu.addAction('Action 2', lambda: logger.info('Action 2 triggered!'))
        return menu
