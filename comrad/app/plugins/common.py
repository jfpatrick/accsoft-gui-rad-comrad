import os
import uuid
import inspect
import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Optional, Union, Iterable, Dict, cast, Type, Generator, Tuple, TypeVar
from types import ModuleType
from enum import Enum, auto, unique
from qtpy.QtWidgets import QWidget, QAction, QMenu
from qtpy.QtGui import QIcon
from qtpy.QtCore import Qt
from pydm.utilities import IconFont


logger = logging.getLogger(__name__)


class CPlugin(metaclass=ABCMeta):
    """Base class for all ComRAD plugins."""

    enabled: bool = True
    """Useful for integrated plugins to mark whether it's enabled by default or should be enabled via launch flag."""

    plugin_id: str = ''
    """Reverse domain string that represents the unique ID of the plugin class."""


class CPositionalPlugin(metaclass=ABCMeta):
    """Base class for ComRAD toolbar plugins."""

    class Position(Enum):
        """Position of the plugin's widget/button in the toolbar/statusbar."""

        LEFT = auto()
        """Positioned on the left items will follow standard items but will be aligned left after them."""

        RIGHT = auto()
        """Positioned on the right items will be sticking to the right edge of the application."""

    position: 'CPositionalPlugin.Position' = Position.LEFT
    """Whether plugin should be positioned following the navigation buttons or on the far right."""

    gravity: int = -1
    """Weight of how much to the side should the plugin be aligned. E.g. if several plugins on the same side are defined,
    and no explicit order is given, how they should be aligned."""


class CActionPlugin(CPlugin, metaclass=ABCMeta):
    """Base class for action-based ComRAD plugins (nav-bar, menubar)."""

    shortcut: Optional[str] = None
    """If defined, shortcut will be applied to the action of the plugin."""

    icon: Union[str, QIcon, None] = None
    """If defined, icon will be applied to the action of the plugin."""

    @abstractmethod
    def triggered(self):
        """Callback when the action is triggered."""
        pass

    @abstractmethod
    def title(self) -> str:
        """Title of the action."""
        pass

    def create_action(self, config: Optional[Dict[str, str]]) -> QAction:
        """
        Factory method to create the action from the properties defined in this class.
        Each more concrete implementation (e.g. :class:`CToolbarActionPlugin`) can define its own way of
        creating action objects.

        Args:
            config: ATTENTION! This argument is currently not being used. It is left for extensibility in the future,
                    similar to the approach taken by :meth:`CWidgetPlugin.create_widget`.

        Returns:
            New action object.
        """
        action = QAction()
        action.setShortcutContext(Qt.ApplicationShortcut)
        if self.shortcut is not None:
            action.setShortcut(self.shortcut)
        if isinstance(self.icon, str):
            font = IconFont()
            action.setIcon(font.icon(self.icon))
        elif isinstance(self.icon, QIcon):
            action.setIcon(self.icon)
        action.triggered.connect(self.triggered)
        action.setText(self.title())
        return action


@unique
class CToolbarID(Enum):
    """Enum to identify predefined toolbar items that already exist in ComRAD by default."""

    SEPARATOR = 'comrad.sep'
    """Toolbar separator"""

    NAV_BACK = 'comrad.back'
    """Navigation button back"""

    NAV_FORWARD = 'comrad.fwd'
    """Navigation button forward"""

    NAV_HOME = 'comrad.home'
    """Navigation button Home"""

    SPACER = 'comrad.spacer'
    """Separating empty space between left-aligned toolbar items and right-aligned ones."""


class CToolbarPlugin(metaclass=ABCMeta):
    """Base class for toolbar ComRAD plugins."""
    pass


class CToolbarActionPlugin(CActionPlugin, CPositionalPlugin, CToolbarPlugin, metaclass=ABCMeta):
    """Base class for action-based ComRAD toolbar plugins."""

    show_in_menu: bool = True
    """In addition to displaying the plugin in toolbar, add it to "Plugins->Toolbar" menu."""


class CWidgetPlugin(CPlugin, CPositionalPlugin, metaclass=ABCMeta):
    """Base class for ComRAD plugins that render as widgets."""

    @abstractmethod
    def create_widget(self, config: Optional[Dict[str, str]]) -> QWidget:
        """
        Instantiate a widget to be rendered in GUI.

        Args:
            config: Launch configuration that is injected by ``--window-plugin-config`` flag. The keys get matched with
                    plugin ID and are combined into a dictionary. Hence, if an app is launched with the flag
                    ``--window-plugin-config com.example.plugin.config1=val1 com.example.plugin.config2=val2``, the
                    ``config`` argument will be a dictionary ``{'config1': 'val1', 'config2': val2'}``. If
                    ``--window-plugin-config`` was not provided by the user, or does not contain any keys for the
                     current widget, ``config`` value will be :obj:`None`.
        """
        pass


class CToolbarWidgetPlugin(CWidgetPlugin, CToolbarPlugin, metaclass=ABCMeta):
    """Base class for widget-based ComRAD toolbar plugins."""
    pass


class CMenuBarPlugin(CPlugin, metaclass=ABCMeta):
    """Base class for ComRAD main menu plugins."""

    @abstractmethod
    def top_level(self) -> Union[str, Iterable[str]]:
        """Name of the top level menu or path to the submenu.

        If a menu with such name exists, the actions will be appended to the end of the menu. Otherwise, a new menu
        will be created
        """
        pass

    @abstractmethod
    def menu_item(self) -> Union[QAction, QMenu]:
        """Actual menu item to inject.

        If it's a QAction, then a simple item will be created, otherwise a submenu will be created."""
        pass


class CStatusBarPlugin(CWidgetPlugin, metaclass=ABCMeta):
    """Base class for ComRAD status bar plugins."""

    is_permanent: bool = False
    """Type of the widget (normal/permanent).

    For explanation of types, refer to the official docs: https://doc.qt.io/qt-5/qstatusbar.html#details.

    Also, widgets are aligned based on their type. Permanent widgets will be placed on the right hand side from
    temporary ones to minimize the likelihood of overlapping with temporary messages. This will override the preference
    defined by `position` property."""


_T = TypeVar('_T', bound=CPlugin)


def load_plugins_from_path(locations: Iterable[Path], token: str, base_type: Type[CPlugin] = CPlugin):
    """
    Load plugins from file locations that match a specific token.

    Args:
        locations: list of file locations.
        token: a phrase that must match the end of the filename for it to be checked for.
        base_type: Base class of the plugins to look for. It should be a subclass of / or :class:`CPlugin`.

    Returns:
        dictionary of plugins add from this folder.
    """
    import importlib.util
    import importlib.machinery
    plugin_classes: Dict[str, ModuleType] = {}
    for loc in locations:
        for root, _, files in os.walk(loc):
            root_path = Path(root)
            if root_path.name.startswith('__'):
                continue

            logger.debug(f'Looking for plugins at: {root_path}')
            for name in files:
                if not name.endswith(token):
                    continue
                temp_name = str(uuid.uuid4())
                logger.debug(f'Trying to load {name} (as {temp_name})...')
                spec = importlib.util.spec_from_file_location(name=temp_name, location=root_path / name)
                if spec is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
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


def filter_enabled_plugins(plugins: Iterable[Type[_T]],
                           whitelist: Optional[Iterable[str]],
                           blacklist: Optional[Iterable[str]]) -> Generator[Tuple[str, Type[_T]], None, None]:

    def extract_type_attr(plugin_class: Type[_T], attr_name: str):
        val = getattr(plugin_class, attr_name, None)
        if val is None or (not isinstance(val, bool) and not val):
            # Allow False, but do not allow empty strings, lists, etc
            logger.exception(f'Plugin "{plugin_class.__name__}" is missing "{attr_name}" class attribute '
                             f'that is essential for all window plugins')
            raise AttributeError
        return val

    for plugin_type in plugins:
        try:
            plugin_id: str = extract_type_attr(plugin_type, 'plugin_id')
            is_enabled: bool = extract_type_attr(plugin_type, 'enabled')
        except AttributeError:
            continue

        if not is_enabled and whitelist and plugin_id in whitelist:
            is_enabled = True
            logger.debug(f'Enabling whitelisted plugin "{plugin_type.__name__}"')
        elif is_enabled and blacklist and plugin_id in blacklist:
            is_enabled = False
            logger.debug(f'Disabling blacklisted plugin "{plugin_type.__name__}"')

        if not is_enabled:
            continue
        yield plugin_id, plugin_type
