import logging
from comrad import CToolbarActionPlugin


logger = logging.getLogger('Demo plugin')


class DemoActionPlugin(CToolbarActionPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.demo'
    shortcut = 'Ctrl+Shift+B'
    icon = 'android'  # Taken from fontawesome map available in PyDM

    def triggered(self):
        logger.info('Action triggered!')

    def title(self) -> str:
        return 'Click me!'
