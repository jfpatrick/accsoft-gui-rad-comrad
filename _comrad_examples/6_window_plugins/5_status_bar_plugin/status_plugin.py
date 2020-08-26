import logging
from qtpy.QtWidgets import QWidget, QLabel
from comrad import CStatusBarPlugin


logger = logging.getLogger('Demo plugin')


class PermanentPlugin(CStatusBarPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.status-permanent'
    is_permanent = True
    position = CStatusBarPlugin.Position.RIGHT

    def create_widget(self) -> QWidget:
        return QLabel('Permanent plugin')


class TempPlugin(CStatusBarPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.status-temp'

    def create_widget(self) -> QWidget:
        return QLabel('Temporary plugin')
