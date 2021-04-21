from typing import cast
from accwidgets.rbac import RbaButton
from comrad import CApplication
from comrad.app.plugins.common import CToolbarWidgetPlugin


class RbaToolbarPlugin(CToolbarWidgetPlugin):
    """Plugin to display RBAC button in the toolbar."""

    position = CToolbarWidgetPlugin.Position.RIGHT
    plugin_id = 'comrad.rbac'
    gravity = 999

    def create_widget(self, _):
        app = cast(CApplication, CApplication.instance())
        widget = RbaButton()
        app.rbac.replace_model(widget.model)
        return widget
