import os
import logging
import json
import subprocess
from pathlib import Path
from itertools import chain
from typing import Optional, List, Dict, Iterable, Type, Union, cast, Tuple
from qtpy.QtWidgets import QAction, QMenu, QSpacerItem, QSizePolicy, QWidget, QHBoxLayout, QMessageBox
from qtpy.QtCore import Qt
from .main_window import CMainWindow  # This has to be above PyDMApplication to ensure monkey-patching
from pydm.application import PyDMApplication
from pydm.utilities import path_info, which
from pydm.data_plugins import is_read_only
from comrad.icons import icon
from comrad.rbac import CRBACState
from .plugins.common import (load_plugins_from_path, CToolbarActionPlugin, CActionPlugin, CToolbarWidgetPlugin,
                             CPositionalPlugin, CToolbarID, CPluginPosition, CPlugin, CMenuBarPlugin, CStatusBarPlugin,
                             CToolbarPlugin)


logger = logging.getLogger(__name__)


_APP_NAME = 'ComRAD'


class CApplication(PyDMApplication):

    def __init__(self,
                 ccda_endpoint: str,
                 ui_file: Optional[str] = None,
                 command_line_args: Optional[List[str]] = None,
                 display_args: Optional[List[str]] = None,
                 use_inca: bool = True,
                 cmw_env: Optional[str] = None,
                 java_env: Optional[Dict[str, str]] = None,
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
                 toolbar_order: Optional[Iterable[Union[str, CToolbarID]]] = None,
                 plugin_whitelist: Optional[Iterable[str]] = None,
                 plugin_blacklist: Optional[Iterable[str]] = None,
                 fullscreen: bool = False):
        """
        :class:`CApplication` handles loading ComRAD display files, opening
        new windows, and most importantly, establishing and managing
        connections to channels via data plugins.

        Args:
            ccda_endpoint: Location of CCDA web service.
            ui_file: The file path to a PyDM display file (.ui or .py).
            command_line_args: A list of strings representing arguments supplied at the command
                line.  All arguments in this list are handled by :class:`PyQt5.QtWidgets.QApplication`,
                in addition to :class:`CApplication`.
            display_args: A list of command line arguments that should be forwarded to the
                :class:`CDisplay` class. This is only useful if a :class:`CRelatedDisplayButton`
                is opening up a .py file with extra arguments specified, and
                probably isn't something you will ever need to use when writing
                code that instantiates :class:`CApplication`.
            use_inca: Whether to route JAPC connection through known InCA servers.
            cmw_env: Original CMW environment. While it is not directly used in this instance, instead relying on
                ``java_env`` and ``ccda_endpoint``, it will be passed to any child ComRAD processes.
            java_env: JVM flags to be passed to the control system libraries.
            perfmon: Whether or not to enable performance monitoring using ``psutil``.
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
            use_main_window: If "ui_file" is not given, this parameter controls whether or not to
                create a :class:`~pydm.main_window.PyDMMainWindow` in the initialization (Default is ``True``).
            nav_bar_plugin_path: Path to the directory with navigation bar (toolbar) plugins. This path has
                can be augmented by ``COMRAD_TOOLBAR_PLUGIN_PATH`` environment variable.
            status_bar_plugin_path: Path to the directory with status bar plugins. This path has
                can be augmented by ``COMRAD_STATUSBAR_PLUGIN_PATH`` environment variable.
            menu_bar_plugin_path: Path to the directory with main menu plugins. This path has
                can be augmented by ``COMRAD_MENUBAR_PLUGIN_PATH`` environment variable.
            stylesheet_path: Path to the *.qss file styling application and widgets.
            fullscreen: Whether or not to launch PyDM in a full screen mode.
        """
        args = [_APP_NAME]
        args.extend(command_line_args or [])
        self.rbac = CRBACState()  # We must keep it before super because dependant plugins will be initialized in super()
        self.ccda_endpoint = ccda_endpoint
        self.cmw_env = cmw_env
        self.use_inca = use_inca
        self.jvm_flags = java_env
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
        self.main_window: CMainWindow = self.main_window  # Just to make code completion work
        self._plugins_menu: Optional[QMenu] = None
        self.setWindowIcon(icon('app'))

        # Useful for subprocesses
        self._stylesheet_path = stylesheet_path
        self._nav_bar_plugin_path = nav_bar_plugin_path
        self._status_bar_plugin_path = status_bar_plugin_path
        self._menu_bar_plugin_path = menu_bar_plugin_path
        self._toolbar_order = toolbar_order
        self._plugin_whitelist = plugin_whitelist
        self._plugin_blacklist = plugin_blacklist
        self._perfmon = perfmon

        self._stored_plugins: List[CPlugin] = []  # Reference plugins to keep the objects alive

        order: Optional[List[Union[str, CToolbarID]]] = None
        if toolbar_order is not None:

            def _convert(identifier: Union[str, CToolbarID]) -> Union[str, CToolbarID]:
                try:
                    return CToolbarID(identifier)
                except ValueError:
                    # Not a valid CToolbarID identifier
                    return identifier

            order = list(map(_convert, toolbar_order))

        self._stored_plugins.extend(self._load_toolbar_plugins(nav_bar_plugin_path,
                                                               order=order,
                                                               whitelist=plugin_whitelist,
                                                               blacklist=plugin_blacklist) or [])
        self._stored_plugins.extend(self._load_menubar_plugins(menu_bar_plugin_path,
                                                               whitelist=plugin_whitelist,
                                                               blacklist=plugin_blacklist) or [])
        self._stored_plugins.extend(self._load_status_bar_plugins(status_bar_plugin_path,
                                                                  whitelist=plugin_whitelist,
                                                                  blacklist=plugin_blacklist) or [])

    def new_pydm_process(self,
                         ui_file: str,
                         macros: Optional[Dict[str, str]] = None,
                         command_line_args: Optional[List[str]] = None):
        """
        Overrides the subclass method to spawn ComRAD process instead of bare PyDM.

        Args:
            ui_file: The path to a .ui or .py file to open in the new process.
            macros: A dictionary of macro variables to supply to the display file to be opened.
            command_line_args: A list of command line arguments to pass to the new process. Typically,
                this argument is used by related display buttons
                to pass in extra arguments.  It is probably rare that code you
                write needs to use this argument.
        """
        # Expand user (~ or ~user) and environment variables.
        ui_file_path = Path(ui_file).expanduser().resolve()
        base_dir, file_name, args = path_info(str(ui_file_path))
        filepath = Path(base_dir) / file_name
        filepath_args = args
        exec_path: Optional[str] = which('comrad')

        if exec_path is None:
            extra_path = os.environ.get('PYDM_PATH', None)
            if extra_path is not None:
                exec_path = str(Path(extra_path) / 'comrad')
            else:
                logger.error('Cannot find "comrad" executable')
                return

        args = [exec_path, 'run']
        if self.hide_nav_bar:
            args.append('--hide-nav-bar')
        if self.hide_menu_bar:
            args.append('--hide-menu-bar')
        if self.hide_status_bar:
            args.append('--hide-status-bar')
        if self.fullscreen:
            args.append('--fullscreen')
        if is_read_only():
            args.append('--read-only')
        if self._perfmon:
            args.append('--perfmon')
        if self._stylesheet_path:
            args.extend(['--stylesheet', self._stylesheet_path])
        if macros is not None:
            args.extend(['-m', json.dumps(macros)])
        if not self.use_inca:
            args.append('--no-inca')
        if self.jvm_flags:
            java_env = '--java-env'
            for key, val in self.jvm_flags:
                java_env += f' {key}={val}'
            args.append(java_env)
        if self.cmw_env:
            args.extend(['--cmw-env', self.cmw_env])
        if self._nav_bar_plugin_path:
            args.extend(['--nav-plugin-path', self._nav_bar_plugin_path])
        if self._status_bar_plugin_path:
            args.extend(['--status-plugin-path', self._status_bar_plugin_path])
        if self._menu_bar_plugin_path:
            args.extend(['--menu-plugin-path', self._menu_bar_plugin_path])
        if self._toolbar_order:

            def _toolbar_to_str(val: Union[str, CToolbarID]):
                return val if isinstance(val, str) else val.value

            args.extend(['--nav-bar-order', ','.join(map(_toolbar_to_str, self._toolbar_order))])
        if self._plugin_whitelist:
            args.extend(['--enable-plugins', ','.join(self._plugin_whitelist)])
        if self._plugin_blacklist:
            args.extend(['--disable-plugins', ','.join(self._plugin_blacklist)])
        args.extend(['--log-level', logging.getLevelName(logging.getLogger('').getEffectiveLevel())])
        args.append(filepath)
        args.extend(self.display_args)
        args.extend(filepath_args)
        if command_line_args is not None:
            args.extend(command_line_args)
        subprocess.Popen(args, shell=False)

    def on_control_error(self, message: str, display_popup: bool):
        """Callback to display a message whenever an exception happens in the control system."""
        logger.warning(f'Control system warning received: {message}')
        if display_popup:
            QMessageBox.warning(None, 'Control system problem', message)

    def _load_toolbar_plugins(self,
                              cmd_line_paths: Optional[str],
                              order: Optional[List[Union[str, CToolbarID]]] = None,
                              whitelist: Optional[Iterable[str]] = None,
                              blacklist: Optional[Iterable[str]] = None) -> Optional[List[CPlugin]]:
        toolbar_plugins = CApplication._load_plugins(env_var_path_key='COMRAD_TOOLBAR_PLUGIN_PATH',
                                                     cmd_line_paths=cmd_line_paths,
                                                     shipped_plugin_path='toolbar',
                                                     base_type=CToolbarPlugin)
        if not toolbar_plugins:
            return None

        toolbar_actions: List[QAction] = []
        toolbar_left: List[Union[QAction, QWidget]] = []  # Items preceding spacer
        toolbar_right: List[Union[QAction, QWidget]] = []  # Items succeeding spacer

        stored_plugins: List[CPlugin] = []

        for plugin_id, plugin_type in CApplication._filter_enabled_plugins(plugins=toolbar_plugins.values(),
                                                                           blacklist=blacklist,
                                                                           whitelist=whitelist):
            if order is not None and plugin_id not in order:
                logger.debug(f'Skipping init for "{plugin_type.__name__}", as it is not going to be used.')
                # Do not instantiate a plugin that is not going to be used
                continue

            item: Union[QAction, QWidget]
            plugin: CToolbarPlugin
            logger.debug(f'Instantiating plugin "{plugin_type.plugin_id}"')
            if issubclass(plugin_type, CActionPlugin):
                action_plugin = cast(CToolbarActionPlugin, plugin_type())
                item = QAction(self.main_window)
                item.setShortcutContext(Qt.ApplicationShortcut)
                if action_plugin.shortcut is not None:
                    item.setShortcut(action_plugin.shortcut)
                if action_plugin.icon is not None:
                    item_icon = (self.main_window.iconFont.icon(action_plugin.icon)
                                 if isinstance(action_plugin.icon, str) else action_plugin.icon)
                    item.setIcon(item_icon)
                item.triggered.connect(action_plugin.triggered)
                item.setText(action_plugin.title())
                toolbar_actions.append(item)
                stored_plugins.append(action_plugin)
                plugin = action_plugin
            else:
                widget_plugin = cast(CToolbarWidgetPlugin, plugin_type())
                item = widget_plugin.create_widget()
                stored_plugins.append(widget_plugin)
                plugin = widget_plugin

            setattr(item, 'plugin_id', plugin_id)  # noqa: B010

            (toolbar_left if cast(CPositionalPlugin, plugin).position == CPluginPosition.LEFT
             else toolbar_right).append(item)

        if toolbar_actions:
            menu = self.main_window._get_or_create_menu(name=('Plugins', 'Toolbar'))
            menu.addActions(toolbar_actions)

        def _add_item_to_nav_bar(item: Union[QWidget, QAction]):
            nav_bar = self.main_window.ui.navbar
            if isinstance(item, QWidget):
                nav_bar.addWidget(item)
            elif isinstance(item, QAction):
                nav_bar.addAction(item)

        def _add_toolbar_spacer():
            # Add spacer to compress toolbar items when possible
            spacer = QWidget()
            layout = QHBoxLayout()
            spacer.setLayout(layout)
            layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
            self.main_window.ui.navbar.addWidget(spacer)

        # If we have sequence supplied, we need to re-order toolbar items
        if order is not None:
            self.main_window.ui.navbar.clear()
            stayed_empty = True
            for next_id in order:
                if isinstance(next_id, str):
                    try:
                        next_item = next((item for item in chain(toolbar_left, toolbar_right)
                                          if getattr(item, 'plugin_id') == next_id))
                        logger.debug(f'Adding toolbar item "{next_id}"')
                    except StopIteration:
                        logger.warning(f'Cannot find "{next_id}" amongst available '
                                       f'toolbar items. It will not be placed')
                        continue
                    _add_item_to_nav_bar(next_item)
                else:
                    if next_id == CToolbarID.SPACER:
                        _add_toolbar_spacer()
                        logger.debug('Adding toolbar spacer')
                    elif next_id == CToolbarID.SEPARATOR:
                        self.main_window.ui.navbar.addSeparator()
                        logger.debug('Adding toolbar separator')
                    elif next_id == CToolbarID.NAV_BACK:
                        _add_item_to_nav_bar(self.main_window.ui.actionBack)
                        logger.debug('Adding toolbar back')
                    elif next_id == CToolbarID.NAV_FORWARD:
                        _add_item_to_nav_bar(self.main_window.ui.actionForward)
                        logger.debug('Adding toolbar forward')
                    elif next_id == CToolbarID.NAV_HOME:
                        _add_item_to_nav_bar(self.main_window.ui.actionHome)
                        logger.debug('Adding toolbar home')
                    else:
                        continue
                stayed_empty = False

            if stayed_empty:
                logger.info(f'No items are placed in nav bar, it will be hidden by default')
                self.main_window.toggle_nav_bar(False)  # FIXME: There is a bug in PyDMMainWindow. When navbar is hidden by default, its menu action is marked as checked
        else:
            self.main_window.ui.navbar.addSeparator()
            for item in toolbar_left:
                _add_item_to_nav_bar(item)
            _add_toolbar_spacer()
            for item in toolbar_right:
                _add_item_to_nav_bar(item)

        return stored_plugins

    def _load_menubar_plugins(self,
                              cmd_line_paths: Optional[str],
                              whitelist: Optional[Iterable[str]] = None,
                              blacklist: Optional[Iterable[str]] = None) -> Optional[List[CPlugin]]:
        menubar_plugins = CApplication._load_plugins(env_var_path_key='COMRAD_MENUBAR_PLUGIN_PATH',
                                                     cmd_line_paths=cmd_line_paths,
                                                     shipped_plugin_path='menu',
                                                     base_type=CMenuBarPlugin)
        if not menubar_plugins:
            return None

        stored_plugins: List[CPlugin] = []

        for _, plugin_type in CApplication._filter_enabled_plugins(plugins=menubar_plugins.values(),
                                                                   whitelist=whitelist,
                                                                   blacklist=blacklist):
            logger.debug(f'Instantiating plugin "{plugin_type.plugin_id}"')
            plugin: CMenuBarPlugin = plugin_type()
            try:
                menu = self.main_window.get_or_create_menu(plugin.top_level())
            except ValueError as ex:
                logger.exception(ex)
                continue

            item = plugin.menu_item()
            if isinstance(item, QAction):
                menu.addAction(item)
                item.setParent(menu)  # Needed, because QWidget.addAction(QAction) call does not transfer ownership
            elif isinstance(item, QMenu):
                # For whatever reason, QMenu.addMenu(QMenu) works funny (overlapping menus over one another).
                # Workaround here, is to create a completely new menu, reassign actions to it, but keep the original
                # object alive (by assigning parent below) in order for lambda-based functors to still work on
                # action trigger...
                new_menu = menu.addMenu(item.title())
                for action in item.actions():
                    item.removeAction(action)
                    new_menu.addAction(action)
                    action.setParent(menu)
                item.setParent(menu)
            else:
                logger.exception(f'Unsupported {plugin_type.__name__}.menu_item() return type '
                                 f'({type(item).__name__}). Must be either QAction or QMenu.')
                continue
            stored_plugins.append(plugin)

        return stored_plugins

    def _load_status_bar_plugins(self,
                                 cmd_line_paths: Optional[str],
                                 whitelist: Optional[Iterable[str]] = None,
                                 blacklist: Optional[Iterable[str]] = None) -> Optional[List[CPlugin]]:
        status_bar_plugins = CApplication._load_plugins(env_var_path_key='COMRAD_STATUSBAR_PLUGIN_PATH',
                                                        cmd_line_paths=cmd_line_paths,
                                                        shipped_plugin_path='statusbar',
                                                        base_type=CStatusBarPlugin)
        if not status_bar_plugins:
            return None

        status_bar_left: List[Tuple[QWidget, bool]] = []  # Items preceding spacer
        status_bar_right: List[Tuple[QWidget, bool]] = []  # Items succeeding spacer

        stored_plugins: List[CPlugin] = []
        for _, plugin_type in CApplication._filter_enabled_plugins(plugins=status_bar_plugins.values(),
                                                                   whitelist=whitelist,
                                                                   blacklist=blacklist):
            logger.debug(f'Instantiating plugin "{plugin_type.plugin_id}"')
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

        all_plugin_paths = str(Path(__file__).parent / 'plugins' / shipped_plugin_path)

        if cmd_line_paths:
            all_plugin_paths = f'{cmd_line_paths}:{all_plugin_paths}'

        extra_plugin_paths: str = ''
        try:
            extra_plugin_paths = os.environ[env_var_path_key]
        except KeyError:
            pass
        if extra_plugin_paths:
            all_plugin_paths = f'{extra_plugin_paths}:{all_plugin_paths}'

        locations = [Path(p) for p in all_plugin_paths.split(':')]
        return load_plugins_from_path(locations=locations,
                                      token='_plugin.py',
                                      base_type=base_type)

    @staticmethod
    def _filter_enabled_plugins(plugins: Iterable[Type[CPlugin]],
                                whitelist: Optional[Iterable[str]],
                                blacklist: Optional[Iterable[str]]):

        def extract_type_attr(plugin_class: Type[CPlugin], attr_name: str):
            val = getattr(plugin_class, attr_name, None)
            if val is None or (not isinstance(val, bool) and not val):
                # Allow False, but do not allow empty strings, lists, etc
                logger.exception(f'Plugin "{plugin_class.__name__}" is missing "{attr_name}" class attribute '
                                 f'that is essential for all toolbar plugins')
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
