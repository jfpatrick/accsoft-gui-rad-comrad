import abc
import os
import uuid
import inspect
import logging
import importlib
from typing import Optional, Union, Iterable, Dict, List, cast, Type
from types import ModuleType
from enum import Enum, auto, unique
from qtpy.QtWidgets import QWidget, QAction, QMenu
from qtpy.QtGui import QIcon


logger = logging.getLogger(__name__)


class CPlugin(metaclass=abc.ABCMeta):
    """Base class for all ComRAD plugins."""

    enabled: bool = True
    """Useful for integrated plugins to mark whether it's enabled by default or should be enabled via launch flag."""

    plugin_id: str = ''
    "Reverse domain string that represents the unique ID of the plugin class."


class CPluginPosition(Enum):
    """Position of the plugin's widget/button in the toolbar/statusbar."""

    LEFT = auto()
    """Positioned on the left items will follow standard items but will be aligned left after them."""

    RIGHT = auto()
    """Positioned on the right items will be sticking to the right edge of the application."""


class CPositionalPlugin(metaclass=abc.ABCMeta):
    """Base class for ComRAD toolbar plugins."""

    position: CPluginPosition = CPluginPosition.LEFT
    """Whether plugin should be positioned following the navigation buttons or on the far right."""


class CActionPlugin(CPlugin, metaclass=abc.ABCMeta):
    """Base class for action-based ComRAD plugins (nav-bar, menubar)."""

    shortcut: Optional[str] = None
    """If defined, shortcut will be applied to the action of the plugin."""

    icon: Union[str, QIcon, None] = None
    """If defined, icon will be applied to the action of the plugin."""

    @abc.abstractmethod
    def triggered(self):
        """Callback when the action is triggered."""
        pass

    @abc.abstractmethod
    def title(self) -> str:
        """Title of the action."""
        pass


@unique
class CToolbarID(Enum):

    SEPARATOR = 'comrad.sep'
    "Toolbar separator"

    NAV_BACK = 'comrad.back'
    "Navigation button back"

    NAV_FORWARD = 'comrad.fwd'
    "Navigation button forward"

    NAV_HOME = 'comrad.home'
    "Navigation button Home"

    SPACER = 'comrad.spacer'
    "Separating empty space between left-aligned toolbar items and right-aligned ones."


class CToolbarPlugin(metaclass=abc.ABCMeta):
    """Base class for toolbar ComRAD plugins."""
    pass


class CToolbarActionPlugin(CActionPlugin, CPositionalPlugin, CToolbarPlugin, metaclass=abc.ABCMeta):
    """Base class for action-based ComRAD toolbar plugins."""
    pass


class CWidgetPlugin(CPlugin, CPositionalPlugin, metaclass=abc.ABCMeta):
    """Base class for ComRAD plugins that render as widgets."""

    @abc.abstractmethod
    def create_widget(self) -> QWidget:
        """Instantiate a widget to be rendered in GUI."""
        pass


class CToolbarWidgetPlugin(CWidgetPlugin, CToolbarPlugin, metaclass=abc.ABCMeta):
    """Base class for widget-based ComRAD toolbar plugins."""
    pass


class CMenuBarPlugin(CPlugin, metaclass=abc.ABCMeta):
    """Base class for ComRAD main menu plugins."""

    @abc.abstractmethod
    def top_level(self) -> Union[str, Iterable[str]]:
        """Name of the top level menu or path to the submenu.

        If a menu with such name exists, the actions will be appended to the end of the menu. Otherwise, a new menu
        will be created
        """
        pass

    @abc.abstractmethod
    def menu_item(self) -> Union[QAction, QMenu]:
        """Actual menu item to inject.

        If it's a QAction, then a simple item will be created, otherwise a submenu will be created."""
        pass


class CStatusBarPlugin(CWidgetPlugin, metaclass=abc.ABCMeta):
    """Base class for ComRAD status bar plugins."""

    is_permanent: bool = False
    """Type of the widget (normal/permanent).
    
    For explanation of types, refer to the official docs: https://doc.qt.io/qt-5/qstatusbar.html#details.
    
    Also, widgets are aligned based on their type. Permanent widgets will be placed on the right hand side from
    temporary ones to minimize the likelihood of overlapping with temporary messages. This will override the preference
    defined by `position` property."""


def load_plugins_from_path(locations: List[str], token: str, base_type: Type = CPlugin):
    """
    Load plugins from file locations that match a specific token.

    Returns
    -------
    plugins: dict
        D

    Args:
        locations: list of file locations.
        token: a phrase that must match the end of the filename for it to be checked for.
        base_type: Base class of the plugins to look for. It should be a subclass of / or CPlugin.

    Returns:
        dictionary of plugins add from this folder.
    """
    plugin_classes: Dict[str, ModuleType] = {}
    for loc in locations:
        for root, _, files in os.walk(loc):
            if root.split(os.path.sep)[-1].startswith('__'):
                continue

            logger.debug(f'Looking for plugins at: {root}')
            for name in files:
                if not name.endswith(token):
                    continue
                temp_name = str(uuid.uuid4())
                logger.debug(f'Trying to load {name} (as {temp_name})...')
                spec: importlib.machinery.ModuleSpec = \
                    importlib.util.spec_from_file_location(name=temp_name, location=os.path.join(root, name))
                mod: ModuleType = importlib.util.module_from_spec(spec)
                loader = cast(importlib.machinery.SourceFileLoader, spec.loader)
                try:
                    loader.exec_module(mod)
                except ImportError as ex:
                    logger.exception(f'Cannot import plugin from {name}: {str(ex)}')
                    continue
                classes = {f'{temp_name}:{obj_name}': obj for obj_name, obj in inspect.getmembers(mod)
                           if (inspect.isclass(obj) and issubclass(obj, base_type) and obj is not base_type
                               and not inspect.isabstract(obj))}
                logger.debug(f'Found new plugin classes:\n{classes}')
                plugin_classes.update(classes)
    return plugin_classes
