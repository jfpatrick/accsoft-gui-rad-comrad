import logging
from comrad import CToolbarActionPlugin


logger = logging.getLogger('Demo plugin')


class DemoActionPlugin(CToolbarActionPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.disabled'
    icon = 'automobile'  # Taken form fontawesome map available in PyDM
    enabled = False

    def triggered(self):
        logger.info('Action triggered!')

    def title(self) -> str:
        return "I'm disabled by default"
