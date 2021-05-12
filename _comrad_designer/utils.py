"""
Utilities for Qt Designer integration.
"""

from typing import Type, List, Optional, TypeVar, Union
from pathlib import Path
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QWidget
from qtpy.QtDesigner import QDesignerFormEditorInterface
from pydm.qtdesigner import DesignerHooks
from accwidgets._designer_base import WidgetDesignerPlugin, SupportedExtensionType, WidgetBoxGroup, create_plugin


CWidgetBoxGroup = WidgetBoxGroup
CWidgetBoxGroup.VIRTUAL = 'Invisible Widgets'


_T = TypeVar('_T', bound=WidgetDesignerPlugin)


def qtplugin_factory(widget_class: Type[QWidget],
                     group: Union[str, WidgetBoxGroup],
                     cls: Type[_T] = WidgetDesignerPlugin,
                     extensions: Optional[List[Type[SupportedExtensionType]]] = None,
                     is_container: bool = False,
                     tooltip: Optional[str] = None,
                     whats_this: Optional[str] = None,
                     icon: Optional[QIcon] = None) -> Type:
    """
    Create a Qt designer plugin based on the passed widget class.

    Args:
        widget_class: Widget class that the plugin should be constructed from
        extensions: List of Extensions that the widget should have
        is_container: whether the widget can accommodate other widgets inside
        group: Name of the group to put widget to
        cls: Subclass of :class:`WidgetDesignerPlugin` if you want to customize the behavior of the plugin
        tootip: contents of the tooltip for the widget
        whats_this: contents of the whatsThis for the widget
        icon: Icon path as visible in the Widget Box of the Qt Designer (leave None to resolve by class name)

    Returns:
        Plugin class based on :class:`WidgetDesignerPlugin`
    """
    BaseClass = create_plugin(widget_class=widget_class,
                              group=group,
                              cls=cls,
                              extensions=extensions,
                              is_container=is_container,
                              tooltip=tooltip,
                              whats_this=whats_this,
                              icon_base_path=Path(__file__).absolute().parent)

    class Plugin(BaseClass):  # type: ignore  # Avoid "Variable "BaseClass" is not valid as a type"
        __doc__ = 'ComRAD Designer plugin for {}'.format(widget_class.__name__)

        CUSTOM_INITIALIZER_METHOD = 'init_for_designer'

        def initialize(self, core: QDesignerFormEditorInterface):
            """
            Override parent function to call PyDM Designer hooks, so that is_qt_designer function
            behaves correctly.

            Args:
                core: Form editor interface to use in the initialization.
            """
            if not self.initialized:
                designer_hooks = DesignerHooks()
                designer_hooks.form_editor = core

            super().initialize(core)

        def icon(self):
            if group == CWidgetBoxGroup.HIDDEN:
                # Do not try to resolve icon (most of hidden widgets won't have it anyway)
                return QIcon()
            elif icon is not None:
                return icon
            return super().icon()

        def domXml(self):
            """
            XML Description of the widget's properties.

            This one has tooltip removed compared to accwidgets (to avoid modified state of tooltip by default).
            """
            return (
                '<widget class="{0}" name="{0}">\n'
                '</widget>\n'
            ).format(self.name())

    return Plugin
