from typing import Optional, Dict
from qtpy.QtWidgets import QLabel
from comrad import CToolbarWidgetPlugin


class DemoWidgetPlugin(CToolbarWidgetPlugin):
    """Plugin to demo a plugin configuration."""

    plugin_id = 'com.example.demo'

    def create_widget(self, config: Optional[Dict[str, str]]):
        if config is None or 'name' not in config:
            text = 'Hi, stranger!'
        else:
            text = f"Hi, {config['name']}!"
        lbl = QLabel(text)
        lbl.setIndent(10)
        return lbl
