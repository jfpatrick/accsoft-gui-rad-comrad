import abc
from typing import Optional, Union, Iterable
from enum import Enum, auto, unique
from qtpy.QtWidgets import QWidget, QAction, QMenu
from qtpy.QtGui import QIcon


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
