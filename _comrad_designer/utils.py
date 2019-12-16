"""
Utilities for Qt Designer intergation.
"""

from typing import Type, List, Optional
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QWidget
from pydm.widgets.qtplugin_extensions import RulesExtension
from pydm.widgets.qtplugin_base import PyDMDesignerPlugin


def qtplugin_factory(cls: Type[QWidget],
                     is_container: bool = False,
                     icon: Optional[QIcon] = None,
                     group: str = 'ComRAD Widgets',
                     extensions: Optional[List[RulesExtension]] = None):
    """
    Helper function to create a generic PyDMDesignerPlugin class.

    It is similar to pydm.widgets.qtplugin_base.qtplugin_factory, but adds additional features:
     - specifies different docstring
     - allows specifying an icon that is visible in Qt Designer
     - allows modifying the widget on creation in Qt Designer (useful for setting initial text)

    Args:
        cls: Widget class.
        is_container: Is a container type of a widget.
        icon: Icon as visible in the Widget Box and Object Inspector.
        group: Category of the Widget Box, where the widget should be placed.
        extensions: Extra extensions to apply to a widget.

    Returns:
        New plugin wrapper class.
    """
    # pylint: disable=missing-docstring
    class Plugin(PyDMDesignerPlugin):
        __doc__ = 'ComRAD Designer plugin for {}'.format(cls.__name__)

        def __init__(self):
            """ComRAD Designer widget plugin wrapper."""
            super().__init__(cls=cls, is_container=is_container, group=group, extensions=extensions)
            self._icon = icon

        def icon(self):
            return self._icon or super().icon()

        def domXml(self):
            """
            XML Description of the widget's properties.

            This one has tooltip removed compared to PyDM.
            """
            return (
                '<widget class="{0}" name="{0}">\n'
                '</widget>\n'
            ).format(self.name())

    return Plugin
