from typing import Type, List, Callable
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QWidget
from pydm.widgets.qtplugin_extensions import RulesExtension
from pydm.widgets.qtplugin_base import PyDMDesignerPlugin

def qtplugin_factory(cls: Type,
                     is_container: bool = False,
                     icon: QIcon = None,
                     group: str = 'ComRAD Widgets',
                     on_widget_create: Callable[[QWidget], None] = None,
                     extensions: List[RulesExtension] = None):
    """
    Helper function to create a generic PyDMDesignerPlugin class.

    It is similar to pydm.widgets.qtplugin_base.qtplugin_factory, but adds additional features:
     - specifies different docstring
     - allows specifying an icon that is visible in Qt Designer
     - allows modifying the widget on creation in Qt Designer (useful for setting initial text)

    Args:
        cls: Widget class.
        is_container: Is a container type of a widget.
        group: Category of the Widget Box, where the widget should be placed.
        extensions: Extra extensions to apply to a widget.

    Returns:
        New plugin wrapper class.
    """
    class Plugin(PyDMDesignerPlugin):
        __doc__ = "ComRAD Designer plugin for {}".format(cls.__name__)

        def __init__(self):
            super(Plugin, self).__init__(cls, is_container, group, extensions)
            self._icon = icon

        def icon(self):
            return self._icon or super().icon()

        def createWidget(self, parent: QWidget) -> QWidget:
            widget: QWidget = super().createWidget(parent)
            if on_widget_create is not None:
                on_widget_create(widget)
            return widget

    return Plugin