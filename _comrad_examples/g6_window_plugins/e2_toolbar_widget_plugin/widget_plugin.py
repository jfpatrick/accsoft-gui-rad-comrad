from qtpy.QtWidgets import QLabel
from comrad import CToolbarWidgetPlugin


class DemoWidgetPlugin(CToolbarWidgetPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.demo'

    def create_widget(self, _):
        lbl = QLabel("I'm a demo plugin!")
        lbl.setIndent(10)
        return lbl
