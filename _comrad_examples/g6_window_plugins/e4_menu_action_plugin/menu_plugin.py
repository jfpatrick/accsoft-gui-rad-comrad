import logging
from typing import Union, Iterable
from qtpy.QtWidgets import QAction, QMenu
from comrad import CMenuBarPlugin


logger = logging.getLogger('Demo plugin')


class NewMenuPlugin(CMenuBarPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.new-menu'

    def top_level(self) -> Union[str, Iterable[str]]:
        return 'Demo'

    def menu_item(self) -> Union[QAction, QMenu]:
        item = QAction()
        item.setText('Click me!')
        item.triggered.connect(lambda: logger.info('Plugin triggered!'))
        return item


class NewSubMenuPlugin(CMenuBarPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.new-submenu'

    def top_level(self) -> Union[str, Iterable[str]]:
        return ['Demo', 'Submenu']

    def menu_item(self) -> Union[QAction, QMenu]:
        item = QAction()
        item.setText('Click me!')
        item.triggered.connect(lambda: logger.info('Plugin triggered!'))
        return item


class ExistingMenuPlugin(CMenuBarPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.existing-menu'

    def top_level(self) -> Union[str, Iterable[str]]:
        return 'File'

    def menu_item(self) -> Union[QAction, QMenu]:
        item = QAction()
        item.setText('Click me!')
        item.triggered.connect(lambda: logger.info('Plugin triggered!'))
        return item


class ExistingSubMenuPlugin(CMenuBarPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.existing-submenu'

    def top_level(self) -> Union[str, Iterable[str]]:
        return ['File', 'Demo']

    def menu_item(self) -> Union[QAction, QMenu]:
        item = QAction()
        item.setText('Click me!')
        item.triggered.connect(lambda: logger.info('Plugin triggered!'))
        return item
