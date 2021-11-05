from qtpy.QtGui import QColor
from qtpy.QtWidgets import QColorDialog
from comrad import CToolbarActionPlugin


class DemoActionPlugin(CToolbarActionPlugin):
    """Plugin to demo a plugin system."""

    plugin_id = 'com.example.demo'
    icon = 'paint-brush'  # Taken from fontawesome map available in PyDM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._color = QColor(255, 0, 255)
        self._action = None

    def triggered(self):
        if not self._action:
            return
        # It is advised to pass parents to the created dialogs in order to preserve parent-child chain
        # and common configuration, such as color palette. Action's parent is the main window.
        parent = self._action.parent()
        color = QColorDialog.getColor(self._color, parent)
        if color.isValid():
            self._color = color
            # Title updated after selection
            self._action.setText(self.title_for_color(color))

    def title(self) -> str:
        # Title used initially
        return self.title_for_color(self._color)

    def title_for_color(self, color: QColor):
        return color.name()

    def create_action(self, *args, **kwargs):
        if not self._action:
            self._action = super().create_action(*args, **kwargs)
        return self._action
