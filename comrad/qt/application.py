import os
import logging
from typing import Optional, List, Dict, Iterable, Type, Union, cast, Tuple
from qtpy.QtWidgets import QAction, QMenu, QSpacerItem, QSizePolicy, QWidget, QHBoxLayout
from qtpy.QtCore import Qt, QObject
from pydm.application import PyDMApplication
from pydm.main_window import PyDMMainWindow
from comrad.utils import icon
from .frame_plugins import load_plugins_from_path
from .plugin import (CToolbarActionPlugin, CActionPlugin, CWidgetPlugin, CPositionalPlugin,
                     CPluginPosition, CPlugin, CMenuBarPlugin, CStatusBarPlugin)


logger = logging.getLogger(__name__)


_APP_NAME = 'ComRAD'


class CApplication(PyDMApplication):

    def __init__(self, ui_file: Optional[str] = None,
                 command_line_args: Optional[List[str]] = None,
                 display_args: Optional[List[str]] = None,
                 perfmon: bool = False,
                 hide_nav_bar: bool = False,
                 hide_menu_bar: bool = False,
                 hide_status_bar: bool = False,
                 read_only: bool = False,
                 macros: Optional[Dict[str, str]] = None,
                 use_main_window: bool = True,
                 nav_bar_plugin_path: Optional[str] = None,
                 status_bar_plugin_path: Optional[str] = None,
                 menu_bar_plugin_path: Optional[str] = None,
                 stylesheet_path: Optional[str] = None,
                 fullscreen: bool = False):
        """
        Args:
            ui_file: The file path to a PyDM display file (.ui or .py).
            command_line_args: A list of strings representing arguments supplied at the command
                line.  All arguments in this list are handled by QApplication, in addition to CApplication.
            display_args: A list of command line arguments that should be forwarded to the
                Display class. This is only useful if a Related Display Button
                is opening up a .py file with extra arguments specified, and
                probably isn't something you will ever need to use when writing
                code that instantiates CApplication.
            perfmon: Whether or not to enable performance monitoring using 'psutil'.
                When enabled, CPU load information on a per-thread basis is
                periodically printed to the terminal.
            hide_nav_bar: Whether or not to display the navigation bar (forward/back/home buttons)
                when the main window is first displayed.
            hide_menu_bar:  Whether or not to display the menu bar (File, View)
                when the main window is first displayed.
            hide_status_bar: Whether or not to display the status bar (general messages and errors)
                when the main window is first displayed.
            read_only: Whether or not to launch PyDM in a read-only state.
            macros: A dictionary of macro variables to be forwarded to the display class being loaded.
            use_main_window: If ui_file is note given, this parameter controls whether or not to
                create a PyDMMainWindow in the initialization (Default is True).
            nav_bar_plugin_path: Path to the directory with navigation bar (toolbar) plugins. This path has
                can be augmented by COMRAD_TOOLBAR_PLUGIN_PATH environment variable.
            status_bar_plugin_path: Path to the directory with status bar plugins. This path has
                can be augmented by COMRAD_STATUSBAR_PLUGIN_PATH environment variable.
            menu_bar_plugin_path: Path to the directory with main menu plugins. This path has
                can be augmented by COMRAD_MENUBAR_PLUGIN_PATH environment variable.
            stylesheet_path: Path to the *.qss file styling application and widgets.
            fullscreen: Whether or not to launch PyDM in a full screen mode.
        """
        args = [_APP_NAME]
        args.extend(command_line_args or [])
        super().__init__(ui_file=ui_file,
                         command_line_args=args,
                         display_args=display_args or [],
                         perfmon=perfmon,
                         hide_menu_bar=hide_menu_bar,
                         hide_nav_bar=hide_nav_bar,
                         hide_status_bar=hide_status_bar,
                         read_only=read_only,
                         macros=macros,
                         use_main_window=use_main_window,
                         stylesheet_path=stylesheet_path,
                         fullscreen=fullscreen)
        self.main_window: PyDMMainWindow = self.main_window  # Just to make code completion work
        self._plugins_menu: Optional[QMenu] = None
        self.setWindowIcon(icon('app', file_path=__file__))
        self.main_window.setWindowTitle('ComRAD Main Window')
        self._stored_plugins: List[CPlugin] = []  # Reference plugins to keep the objects alive

        self._stored_plugins.extend(self._load_toolbar_plugins(nav_bar_plugin_path) or [])
        self._stored_plugins.extend(self._load_menubar_plugins(menu_bar_plugin_path) or [])
        self._stored_plugins.extend(self._load_status_bar_plugins(status_bar_plugin_path) or [])
        # TODO: Add exit menu item

    def _load_toolbar_plugins(self, cmd_line_paths: Optional[str]) -> Optional[List[CPlugin]]:
        toolbar_plugins = CApplication._load_plugins(env_var_path_key='COMRAD_TOOLBAR_PLUGIN_PATH',
                                                     cmd_line_paths=cmd_line_paths,
                                                     shipped_plugin_path='toolbar',
                                                     base_type=CPositionalPlugin)
        if not toolbar_plugins:
            return None

        self.main_window.ui.navbar.addSeparator()

        toolbar_actions: List[QAction] = []
        toolbar_left: List[Union[QAction, QWidget]] = []  # Items preceding spacer
        toolbar_right: List[Union[QAction, QWidget]] = []  # Items succeeding spacer

        stored_plugins: List[CPlugin] = []

        for plugin_type in toolbar_plugins.values():
            plugin: Union[CToolbarActionPlugin, CWidgetPlugin]
            if issubclass(plugin_type, CActionPlugin):
                action_plugin = cast(CToolbarActionPlugin, plugin_type())
                item = QAction(self.main_window)
                item.setShortcutContext(Qt.ApplicationShortcut)
                if action_plugin.shortcut is not None:
                    item.setShortcut(action_plugin.shortcut)
                if action_plugin.icon is not None:
                    item.setIcon(self.main_window.iconFont.icon(action_plugin.icon))
                item.triggered.connect(action_plugin.triggered)
                item.setText(action_plugin.title())
                toolbar_actions.append(item)
                stored_plugins.append(action_plugin)
                plugin = action_plugin
            else:
                widget_plugin = cast(CWidgetPlugin, plugin_type())
                item = widget_plugin.create_widget()
                stored_plugins.append(widget_plugin)
                plugin = widget_plugin

            (toolbar_left if cast(CPositionalPlugin, plugin).position == CPluginPosition.LEFT
             else toolbar_right).append(item)

        if toolbar_actions:
            menu = self._get_or_create_menu(name=('Plugins', 'Toolbar'))
            menu.addActions(toolbar_actions)

        def _add_to_nav_bar(items: Iterable[Union[QWidget, QAction]]):
            nav_bar = self.main_window.ui.navbar
            for item in items:
                if isinstance(item, QWidget):
                    nav_bar.addWidget(item)
                elif isinstance(item, QAction):
                    nav_bar.addAction(item)

        _add_to_nav_bar(toolbar_left)

        # Add spacer to compress toolbar items when possible
        spacer = QWidget()
        layout = QHBoxLayout()
        spacer.setLayout(layout)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.main_window.ui.navbar.addWidget(spacer)

        _add_to_nav_bar(toolbar_right)

        return stored_plugins

    def _get_or_create_menu(self,
                            name: Union[str, Iterable[str]],
                            parent: Optional[QMenu] = None,
                            full_path: Optional[str] = None) -> QMenu:
        parent_menu: QMenu = parent or self.main_window.menuBar()
        full_path = full_path or cast(str, name)
        if isinstance(name, str):
            try:
                menu = next((a.menu() for a in parent_menu.actions() if a.text() == name))
            except StopIteration:
                if isinstance(parent_menu, QMenu):
                    logger.debug(f'Adding new menu "{name}" to parent "{parent_menu.title()}"')
                else:
                    logger.debug(f'Adding new menu "{name}" to menu bar')
                return parent_menu.addMenu(name)
            if menu is None:
                path = full_path if isinstance(full_path, str) else '->'.join(full_path)
                raise ValueError(f'Cannot create submenu "{path}". Another action (not submenu) with '
                                 'this name already exists')
            return menu
        else:
            menu = parent_menu
            for sub_name in name:
                menu = self._get_or_create_menu(name=sub_name, parent=menu, full_path=full_path)
            return menu

    def _load_menubar_plugins(self, cmd_line_paths: Optional[str]) -> Optional[List[CPlugin]]:
        menubar_plugins = CApplication._load_plugins(env_var_path_key='COMRAD_MENUBAR_PLUGIN_PATH',
                                                     cmd_line_paths=cmd_line_paths,
                                                     shipped_plugin_path='menu',
                                                     base_type=CMenuBarPlugin)
        if not menubar_plugins:
            return None

        stored_plugins: List[CPlugin] = []

        for plugin_type in menubar_plugins.values():
            plugin: CMenuBarPlugin = plugin_type()
            try:
                menu = self._get_or_create_menu(name=plugin.top_level())
            except ValueError as ex:
                logger.exception(ex)
                continue

            item = plugin.menu_item()
            if isinstance(item, QAction):
                menu.addAction(item)
                item.setParent(menu)  # Needed, otherwise menu does not appear as has no parent
            elif isinstance(item, QMenu):
                menu.addMenu(item)
                item.setParent(menu)  # Needed, otherwise menu does not appear as has no parent
            else:
                logger.exception(f'Unsupported {plugin_type.__name__}.menu_item() return type '
                                 f'({type(item).__name__}). Must be either QAction or QMenu.')
                continue
            stored_plugins.append(plugin)

        return stored_plugins

    def _load_status_bar_plugins(self, cmd_line_paths: Optional[str]) -> Optional[List[CPlugin]]:
        status_bar_plugins = CApplication._load_plugins(env_var_path_key='COMRAD_STATUSBAR_PLUGIN_PATH',
                                                        cmd_line_paths=cmd_line_paths,
                                                        shipped_plugin_path='statusbar',
                                                        base_type=CStatusBarPlugin)
        if not status_bar_plugins:
            return None

        status_bar_left: List[Tuple[QWidget, bool]] = []  # Items preceding spacer
        status_bar_right: List[Tuple[QWidget, bool]] = []  # Items succeeding spacer

        stored_plugins: List[CPlugin] = []
        for plugin_type in status_bar_plugins.values():
            plugin = cast(CStatusBarPlugin, plugin_type())
            widget = plugin.create_widget()
            item = (widget, plugin.is_permanent)
            (status_bar_left if plugin.position == CPluginPosition.LEFT else status_bar_right).append(item)
            stored_plugins.append(plugin)

        def _add_status_widgets(items: Iterable[Tuple[QWidget, bool]]):
            status_bar = self.main_window.statusBar()
            for widget, is_permanent in items:
                if is_permanent:
                    status_bar.addPermanentWidget(widget)
                else:
                    status_bar.addWidget(widget)

        _add_status_widgets(status_bar_left)

        # Add a spacer separating widgets (by just setting a high stretch)
        self.main_window.statusBar().addWidget(QWidget(), 9999)

        _add_status_widgets(status_bar_right)

        return stored_plugins

    @staticmethod
    def _load_plugins(env_var_path_key: str,
                      cmd_line_paths: Optional[str],
                      shipped_plugin_path: str,
                      base_type: Type = CPlugin) -> Dict[str, Type]:

        all_plugin_paths = os.path.join(os.path.dirname(__file__), shipped_plugin_path)

        if cmd_line_paths:
            all_plugin_paths = f'{cmd_line_paths}:{all_plugin_paths}'

        extra_plugin_paths: str = ''
        try:
            extra_plugin_paths = os.environ[env_var_path_key]
        except KeyError:
            pass
        if extra_plugin_paths:
            all_plugin_paths = f'{extra_plugin_paths}:{all_plugin_paths}'

        locations = all_plugin_paths.split(':')
        return load_plugins_from_path(locations=locations,
                                      token='_plugin.py',
                                      base_type=base_type)


class CAction(QAction):

    def __init__(self, parent: Optional[QObject], *args, plugin: CActionPlugin, **kwargs):
        super().__init__(parent, *args, **kwargs)
        # To keep the plugin object alive
        self._plugin = plugin
