import os
import logging
import platform
import subprocess
from itertools import chain
from pathlib import Path
from typing import Optional, Union, Iterable, cast, Tuple, Type, List, Dict
from qtpy.QtWidgets import (QWidget, QMenu, QAction, QMainWindow, QFileDialog, QApplication, QSizePolicy,
                            QDockWidget, QActionGroup)
from qtpy.QtCore import QCoreApplication, Qt, Signal, QObject, QSize, QTimer
from qtpy.QtGui import QKeySequence
from pydm.pydm_ui import Ui_MainWindow
from pydm.main_window import PyDMMainWindow
from pydm.data_plugins import is_read_only
from accwidgets.log_console import LogConsoleDock
from comrad.monkey import modify_in_place, MonkeyPatchedClass
from comrad.data.context import CContext, CContextProvider
from comrad.widgets.tables import CLogConsole
from .about import AboutDialog
from .plugins.common import (load_plugins_from_path, CToolbarActionPlugin, CActionPlugin, CToolbarWidgetPlugin,
                             CPositionalPlugin, CToolbarID, CPlugin, CMenuBarPlugin, CStatusBarPlugin,
                             CToolbarPlugin, filter_enabled_plugins)
from .plugins._config import WindowPluginConfigTrie


logger = logging.getLogger(__name__)


class CMainWindowSignalHelper(QObject, CContextProvider):

    contextUpdated = Signal()
    """Signal to communicate to children that context needs to be updated and possibly connections need to be re-established."""

    def __init__(self, parent: Optional[QObject] = None):
        """
        Since we can't create signals on the main window, due to monkey-patching approach, we instead keep an object
        owning the signals, which does that.

        Args:
            parent: Parent object.
        """
        QObject.__init__(self, parent)
        CContextProvider.__init__(self)

    @property
    def context_ready(self) -> bool:
        return True

    def get_context_view(self) -> CContext:
        return cast('CMainWindow', self.parent()).window_context


@modify_in_place
class CMainWindow(PyDMMainWindow, CContextProvider, MonkeyPatchedClass):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 hide_nav_bar: bool = False,
                 hide_menu_bar: bool = False,
                 hide_status_bar: bool = False,
                 **kwargs):
        """Main window of ComRAD application. This is a monkey-patched version of :class:`PyDMMainWindow`.

        Args:
            parent: Parent widget of the window.
            hide_nav_bar: Hide navigation bar initially.
            hide_menu_bar: Hide menu bar initially.
            hide_status_bar: Hide status bar initially.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        log_console = CLogConsole()  # Initialize as early as possible, to capture as many logs as possible
        log_console.initialize_loggers()
        # We must attempt initial login before calling super initializer, because that's where the rest of UI
        # initializes, hence devices can get contacted without a proper RBAC token. At the same time, we try
        # to login after log console has been created, so that RBAC logs can be captured. We cannot pass log_console
        # via DI, because this initializer is called from PyDM, and we have no control over that call and its arguments.
        self.__rbac_startup_login()

        self._overridden_members['__init__'](self,
                                             parent=parent,
                                             hide_nav_bar=hide_nav_bar,
                                             hide_menu_bar=hide_menu_bar,
                                             hide_status_bar=hide_status_bar,
                                             **kwargs)
        CContextProvider.__init__(self)
        self._stored_plugins: List[CPlugin] = []  # Reference plugins to keep the objects alive
        self._signal_helper = CMainWindowSignalHelper(self)
        self._icon_factor: float = 1.0
        self._default_icon_size = self.ui.navbar.iconSize()
        self.contextUpdated = self._signal_helper.contextUpdated
        self._window_context = CContext()
        self._window_context.dataFiltersChanged.connect(self.contextUpdated.emit)
        self._window_context.wildcardsChanged.connect(self.contextUpdated.emit)
        self._window_context.selectorChanged.connect(self.contextUpdated.emit)

        # Remove custom Show navigation bar menu item and use the one provided by the widget (toggleViewAction)
        # (because when both are used, their check state gets out of sync
        index = self.ui.menuView.actions().index(self.ui.actionShow_Navigation_Bar)
        if index > -1:
            self.ui.menuView.removeAction(self.ui.actionShow_Navigation_Bar)
            self.ui.menuView.insertAction(self.ui.menuView.actions()[index], self.ui.navbar.toggleViewAction())
            self.ui.actionShow_Navigation_Bar.deleteLater()
            self.ui.actionShow_Navigation_Bar = None

        dock = LogConsoleDock(allowed_areas=Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea, console=log_console)
        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)
        dock.console.expanded = False
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self._console_dock = dock
        log_console_action = cast(QAction, dock.toggleViewAction())
        log_console_action.setText(QCoreApplication.translate('MainWindow', 'Show Log Console'))
        # Insert before "Show status bar"
        self.ui.menuView.insertAction(self.ui.actionShow_Status_Bar, log_console_action)

        # Insert before "Increase Font Size"
        self.ui.menuView.insertSeparator(self.ui.actionIncrease_Font_Size)
        act = QAction(QCoreApplication.translate('MainWindow', 'Increase Icon Size'), self)
        act.triggered.connect(self._increase_icon_size)
        act.setShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_Equal))
        self.ui.menuView.insertAction(self.ui.actionIncrease_Font_Size, act)
        act = QAction(QCoreApplication.translate('MainWindow', 'Decrease Icon Size'), self)
        act.triggered.connect(self._decrease_icon_size)
        act.setShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_Minus))
        self.ui.menuView.insertAction(self.ui.actionIncrease_Font_Size, act)
        act = QAction(QCoreApplication.translate('MainWindow', 'Default Icon Size'), self)
        act.triggered.connect(self._reset_icon_size)
        self.ui.menuView.insertAction(self.ui.actionIncrease_Font_Size, act)
        act.setShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_0))

        style_menu = QMenu(QCoreApplication.translate('MainWindow', 'Navigation Bar Style'), self)
        self._action_navbar_icon = style_menu.addAction(QCoreApplication.translate('MainWindow', 'Icon Only'))
        self._action_navbar_icon.setCheckable(True)
        self._action_navbar_icon.setData(Qt.ToolButtonIconOnly)
        self._action_navbar_text = style_menu.addAction(QCoreApplication.translate('MainWindow', 'Text Only'))
        self._action_navbar_text.setCheckable(True)
        self._action_navbar_text.setData(Qt.ToolButtonTextOnly)
        self._action_navbar_besides = style_menu.addAction(QCoreApplication.translate('MainWindow', 'Text Beside Icon'))
        self._action_navbar_besides.setCheckable(True)
        self._action_navbar_besides.setData(Qt.ToolButtonTextBesideIcon)
        self._action_navbar_under = style_menu.addAction(QCoreApplication.translate('MainWindow', 'Text Under Icon'))
        self._action_navbar_under.setCheckable(True)
        self._action_navbar_under.setData(Qt.ToolButtonTextUnderIcon)
        self._group_navbar = QActionGroup(self)  # Turns separatly checkable actions into a single radio group
        self._group_navbar.addAction(self._action_navbar_icon)
        self._group_navbar.addAction(self._action_navbar_text)
        self._group_navbar.addAction(self._action_navbar_besides)
        self._group_navbar.addAction(self._action_navbar_under)
        self._update_navbar_style_menu(self.ui.navbar.toolButtonStyle())
        style_menu.triggered.connect(self._on_navbar_style_triggered)
        self.ui.navbar.toolButtonStyleChanged.connect(self._update_navbar_style_menu)
        # Insert before "Show File Path in Title Bar"
        self.ui.menuView.insertMenu(self.ui.actionShow_File_Path_in_Title_Bar, style_menu)
        self._style_menu = style_menu

        pos_menu = QMenu(QCoreApplication.translate('MainWindow', 'Navigation Bar Position'), self)
        self._action_navbar_top = pos_menu.addAction(QCoreApplication.translate('MainWindow', 'Top'))
        self._action_navbar_top.setCheckable(True)
        self._action_navbar_top.setData(Qt.TopToolBarArea)
        self._action_navbar_left = pos_menu.addAction(QCoreApplication.translate('MainWindow', 'Left'))
        self._action_navbar_left.setCheckable(True)
        self._action_navbar_left.setData(Qt.LeftToolBarArea)
        self._group_navbar_pos = QActionGroup(self)  # Turns separatly checkable actions into a single radio group
        self._group_navbar_pos.addAction(self._action_navbar_top)
        self._group_navbar_pos.addAction(self._action_navbar_left)
        self._update_navbar_pos_menu(self.toolBarArea(self.ui.navbar))
        self.ui.navbar.orientationChanged.connect(self._update_navbar_pos_menu_from_orientation)
        pos_menu.triggered.connect(self._on_navbar_pos_triggered)
        # Insert before "Show File Path in Title Bar"
        self.ui.menuView.insertMenu(self.ui.actionShow_File_Path_in_Title_Bar, pos_menu)
        self._pos_menu = pos_menu

        self.ui.menuView.insertSeparator(self.ui.actionShow_File_Path_in_Title_Bar)

        # Insert before "Show Connections..."
        self.ui.menuView.insertSeparator(self.ui.actionShow_Connections)

    def hide_log_console(self):
        self._console_dock.hide()

    @property
    def context_ready(self) -> bool:
        return self._signal_helper.context_ready

    def get_context_view(self) -> CContext:
        # This API is used for supply chain (to be consistent between context providers
        # While window_context is used also in the mutable sense, when plugins want to modify global context.
        return self._signal_helper.get_context_view()

    @property
    def window_context(self) -> CContext:
        """Global context for the window. All widgets should obey to it, unless it's overridden by a CContextContainer."""
        return self._window_context

    # FIXME: Connection dialog table regularly updates and annoys user interaction

    def update_window_title(self):
        """Overridden method to enable ComRAD branding."""

        if self.showing_file_path_in_title_bar:
            title = self.current_file()
        else:
            title = self._display_widget.windowTitle()

        # Set the process name for RBAC (visible in Token Information)
        os.environ['RBAC_APPLICATION_NAME'] = title + ' / ComRAD'

        title += ' - ComRAD'
        if is_read_only():
            title += ' [Read Only]'
        self.setWindowTitle(title)

    def show_about_window(self, _):
        """Overridden method to shows custom ComRAD About dialog."""
        AboutDialog(self).show()

    def edit_in_designer(self, _):
        """Overridden slot to open current file in Qt Designer and/or Text editor based on the file type."""
        ui_file, py_file = self.get_files_in_display()
        if py_file:
            self._open_editor_generic(py_file)
        if ui_file:
            self._open_editor_ui(ui_file)

    def open_file_action(self, _):
        """Overridden slot to open file that substitutes the name of the file type visible in the dialog."""
        modifiers = QApplication.keyboardModifiers()
        folder: Path
        try:
            curr_file = Path(self.current_file())
            folder = curr_file.parent
        except IndexError:
            folder = Path.cwd()

        dialog_res = QFileDialog.getOpenFileName(self, 'Open File...', str(folder), 'ComRAD Files (*.ui *.py)')
        filename: str = dialog_res[0] if isinstance(dialog_res, (list, tuple)) else dialog_res

        if filename:
            filename = str(filename)
            try:
                if modifiers == Qt.ShiftModifier:
                    self.app.new_window(filename)
                else:
                    self.open_file(filename)
            except (OSError, ValueError, ImportError) as e:  #
                self.handle_open_file_error(filename, e)

    def load_window_plugins(self,
                            config: WindowPluginConfigTrie,
                            nav_bar_plugin_path: Optional[List[str]] = None,
                            status_bar_plugin_path: Optional[List[str]] = None,
                            menu_bar_plugin_path: Optional[List[str]] = None,
                            plugin_whitelist: Optional[Iterable[str]] = None,
                            plugin_blacklist: Optional[Iterable[str]] = None,
                            toolbar_order: Optional[List[Union[str, CToolbarID]]] = None):
        """
        Loads plugins and places them around the main window.

        Args:
            config: Parsed user configuration for window plugins (``--window-plugin-config`` flag).
            nav_bar_plugin_path: Path(s) to the directory with navigation bar (toolbar) plugins. This path has
                can be augmented by ``COMRAD_TOOLBAR_PLUGIN_PATH`` environment variable.
            status_bar_plugin_path: Path(s) to the directory with status bar plugins. This path has
                can be augmented by ``COMRAD_STATUSBAR_PLUGIN_PATH`` environment variable.
            menu_bar_plugin_path: Path(s) to the directory with main menu plugins. This path has
                can be augmented by ``COMRAD_MENUBAR_PLUGIN_PATH`` environment variable.
            toolbar_order: List of IDs of toolbar items in order in which they must appear left-to-right.
            plugin_whitelist: List of plugin IDs that have to be enabled even if they are disabled by default.
            plugin_blacklist: List of plugin IDs that have to be disabled even if they are enabled by default.


        """
        self._stored_plugins.extend(self._load_toolbar_plugins(config=config,
                                                               cmd_line_paths=nav_bar_plugin_path,
                                                               order=toolbar_order,
                                                               whitelist=plugin_whitelist,
                                                               blacklist=plugin_blacklist) or [])
        self._stored_plugins.extend(self._load_menubar_plugins(cmd_line_paths=menu_bar_plugin_path,
                                                               whitelist=plugin_whitelist,
                                                               blacklist=plugin_blacklist) or [])
        self._stored_plugins.extend(self._load_status_bar_plugins(config=config,
                                                                  cmd_line_paths=status_bar_plugin_path,
                                                                  whitelist=plugin_whitelist,
                                                                  blacklist=plugin_blacklist) or [])

    def _increase_icon_size(self):
        self._icon_factor += 0.1
        self._update_icon_size()

    def _decrease_icon_size(self):
        if self._icon_factor <= 0.1:
            return
        self._icon_factor -= 0.1
        self._update_icon_size()

    def _reset_icon_size(self):
        self._icon_factor = 1.0
        self._update_icon_size()

    def _update_icon_size(self):
        new_size = QSize(self._default_icon_size.width() * self._icon_factor, self._default_icon_size.height() * self._icon_factor)
        self.ui.navbar.setIconSize(new_size)
        QTimer.singleShot(0, self.resizeForNewDisplayWidget)

    def _get_or_create_menu(self,
                            name: Union[str, Iterable[str]],
                            parent: Optional[QMenu] = None,
                            full_path: Optional[str] = None) -> QMenu:
        parent_menu: QMenu = parent or self.menuBar()
        full_path = full_path or cast(str, name)
        logger.debug(f'Searching for menu "{name}" under {parent_menu}')
        if isinstance(name, str):
            try:
                menu = next((a.menu() for a in parent_menu.actions() if a.text() == name))
            except StopIteration:
                if isinstance(parent_menu, QMenu):
                    logger.debug(f'Adding new menu "{name}" to parent "{parent_menu.title()}"')
                else:
                    logger.debug(f'Adding new menu "{name}" to menu bar')
                return parent_menu.addMenu(name)
            logger.debug(f'Found existing menu "{name}": {menu}')
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

    def _open_editor_ui(self, filename: str):
        """Overridden of :meth:`pydm.main_window.PyDMMainWindow.edit_in_designer.open_editor_ui` inner method."""
        if not filename:
            return
        from _comrad.designer import run_designer
        from .application import CApplication
        self.statusBar().showMessage(f"Launching '{filename}' in ComRAD Designer...", 5000)
        app = cast(CApplication, CApplication.instance())
        run_designer(files=[filename],
                     blocking=False,
                     ccda_env=app.ccda_endpoint,
                     use_inca=app.use_inca,
                     selector=self.window_context.selector,
                     java_env=app.jvm_flags)

    def _open_editor_generic(self, filename: str):
        """
        We only care about Linux, but this is (more or less) a direct copy-paste of
        :meth:`pydm.main_window.PyDMMainWindow.edit_in_designer.open_editor_generic` inner method.
        """
        system = platform.system()
        if system == 'Linux':
            subprocess.call(('xdg-open', filename))
        elif system == 'Darwin':
            subprocess.call(('open', filename))
        else:
            logger.warning("You are using unsupported operating system. Can't open the file...")

    def _update_navbar_style_menu(self, new_style: Qt.ToolButtonStyle):
        self._action_navbar_icon.setChecked(new_style == Qt.ToolButtonIconOnly)
        self._action_navbar_text.setChecked(new_style == Qt.ToolButtonTextOnly)
        self._action_navbar_besides.setChecked(new_style == Qt.ToolButtonTextBesideIcon)
        self._action_navbar_under.setChecked(new_style == Qt.ToolButtonTextUnderIcon)

    def _on_navbar_style_triggered(self, action: QAction):
        new_style = action.data()
        self.ui.navbar.setToolButtonStyle(new_style)

    def _update_navbar_pos_menu(self, new_area: Qt.ToolBarArea):
        self._action_navbar_top.setChecked(new_area == Qt.TopToolBarArea)
        self._action_navbar_left.setChecked(new_area == Qt.LeftToolBarArea)

    def _on_navbar_pos_triggered(self, action: QAction):
        new_pos = action.data()
        self.addToolBar(new_pos, self.ui.navbar)

    def _update_navbar_pos_menu_from_orientation(self, new_orientation: Qt.Orientation):
        self._update_navbar_pos_menu(Qt.LeftToolBarArea if new_orientation == Qt.Vertical else Qt.TopToolBarArea)

    def _load_toolbar_plugins(self,
                              config: WindowPluginConfigTrie,
                              cmd_line_paths: Optional[List[str]],
                              order: Optional[List[Union[str, CToolbarID]]] = None,
                              whitelist: Optional[Iterable[str]] = None,
                              blacklist: Optional[Iterable[str]] = None) -> Optional[List[CPlugin]]:
        toolbar_plugins = CMainWindow._load_plugins(env_var_path_key='COMRAD_TOOLBAR_PLUGIN_PATH',
                                                    cmd_line_paths=cmd_line_paths,
                                                    shipped_plugin_path='toolbar',
                                                    base_type=CToolbarPlugin)
        if not toolbar_plugins:
            return None

        toolbar_actions: List[QAction] = []
        toolbar_left: List[Union[QAction, QWidget]] = []  # Items preceding spacer
        toolbar_right: List[Union[QAction, QWidget]] = []  # Items succeeding spacer

        stored_plugins: List[CPlugin] = []

        for plugin_id, plugin_type in filter_enabled_plugins(plugins=toolbar_plugins.values(),
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
                item = action_plugin.create_action(None)
                item.setParent(self)
                if action_plugin.show_in_menu:
                    toolbar_actions.append(item)
                stored_plugins.append(action_plugin)
                plugin = action_plugin
            else:
                widget_plugin = cast(CToolbarWidgetPlugin, plugin_type())
                widget_config = CMainWindow._read_widget_plugin_config(config=config, plugin_id=plugin_type.plugin_id)
                item = widget_plugin.create_widget(widget_config)
                stored_plugins.append(widget_plugin)
                plugin = widget_plugin

            setattr(item, 'plugin_id', plugin_id)  # noqa: B010
            setattr(item, 'plugin_gravity', cast(CPositionalPlugin, plugin).gravity)  # noqa: B010

            (toolbar_left if cast(CPositionalPlugin, plugin).position == CPositionalPlugin.Position.LEFT
             else toolbar_right).append(item)

        toolbar_left.sort(key=lambda x: x.plugin_gravity, reverse=True)
        toolbar_right.sort(key=lambda x: x.plugin_gravity)

        if toolbar_actions:
            menu = self._get_or_create_menu(name=('Plugins', 'Toolbar'))
            menu.addActions(toolbar_actions)

        def _add_item_to_nav_bar(item: Union[QWidget, QAction]):
            nav_bar = self.ui.navbar
            if isinstance(item, QWidget):
                nav_bar.addWidget(item)
            elif isinstance(item, QAction):
                nav_bar.addAction(item)

        def _add_toolbar_spacer():
            # Add spacer to compress toolbar items when possible
            spacer = ToolbarSpacer()
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.ui.navbar.addWidget(spacer)

        # If we have sequence supplied, we need to re-order toolbar items
        if order is not None:
            self.ui.navbar.clear()
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
                        self.ui.navbar.addSeparator()
                        logger.debug('Adding toolbar separator')
                    elif next_id == CToolbarID.NAV_BACK:
                        _add_item_to_nav_bar(self.ui.actionBack)
                        logger.debug('Adding toolbar back')
                    elif next_id == CToolbarID.NAV_FORWARD:
                        _add_item_to_nav_bar(self.ui.actionForward)
                        logger.debug('Adding toolbar forward')
                    elif next_id == CToolbarID.NAV_HOME:
                        _add_item_to_nav_bar(self.ui.actionHome)
                        logger.debug('Adding toolbar home')
                    else:
                        continue
                stayed_empty = False

            if stayed_empty:
                logger.info('No items are placed in nav bar, it will be hidden by default')
                self.toggle_nav_bar(False)  # FIXME: There is a bug in PyDMMainWindow. When navbar is hidden by default, its menu action is marked as checked
        else:
            self.ui.navbar.addSeparator()
            for item in toolbar_left:
                _add_item_to_nav_bar(item)
            _add_toolbar_spacer()
            for idx, item in enumerate(toolbar_right):
                if idx > 0:
                    self.ui.navbar.addSeparator()
                _add_item_to_nav_bar(item)

        return stored_plugins

    def _load_menubar_plugins(self,
                              cmd_line_paths: Optional[List[str]],
                              whitelist: Optional[Iterable[str]] = None,
                              blacklist: Optional[Iterable[str]] = None) -> Optional[List[CPlugin]]:
        menubar_plugins = CMainWindow._load_plugins(env_var_path_key='COMRAD_MENUBAR_PLUGIN_PATH',
                                                    cmd_line_paths=cmd_line_paths,
                                                    shipped_plugin_path='menu',
                                                    base_type=CMenuBarPlugin)
        if not menubar_plugins:
            return None

        stored_plugins: List[CPlugin] = []

        for _, plugin_type in filter_enabled_plugins(plugins=menubar_plugins.values(),
                                                     whitelist=whitelist,
                                                     blacklist=blacklist):
            logger.debug(f'Instantiating plugin "{plugin_type.plugin_id}"')
            plugin: CMenuBarPlugin = plugin_type()
            try:
                menu = self._get_or_create_menu(name=plugin.top_level())
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
                                 config: WindowPluginConfigTrie,
                                 cmd_line_paths: Optional[List[str]],
                                 whitelist: Optional[Iterable[str]] = None,
                                 blacklist: Optional[Iterable[str]] = None) -> Optional[List[CPlugin]]:
        status_bar_plugins = CMainWindow._load_plugins(env_var_path_key='COMRAD_STATUSBAR_PLUGIN_PATH',
                                                       cmd_line_paths=cmd_line_paths,
                                                       shipped_plugin_path='statusbar',
                                                       base_type=CStatusBarPlugin)
        if not status_bar_plugins:
            return None

        status_bar_left: List[Tuple[QWidget, bool, int]] = []  # Items preceding spacer
        status_bar_right: List[Tuple[QWidget, bool, int]] = []  # Items succeeding spacer

        stored_plugins: List[CPlugin] = []
        for _, plugin_type in filter_enabled_plugins(plugins=status_bar_plugins.values(),
                                                     whitelist=whitelist,
                                                     blacklist=blacklist):
            logger.debug(f'Instantiating plugin "{plugin_type.plugin_id}"')
            plugin = cast(CStatusBarPlugin, plugin_type())
            widget_config = CMainWindow._read_widget_plugin_config(config=config, plugin_id=plugin_type.plugin_id)
            widget = plugin.create_widget(widget_config)
            item = (widget, plugin.is_permanent, plugin.gravity)
            (status_bar_left if plugin.position == CPositionalPlugin.Position.LEFT else status_bar_right).append(item)
            stored_plugins.append(plugin)

        status_bar_left.sort(key=lambda x: x[2], reverse=True)
        status_bar_right.sort(key=lambda x: x[2])

        def _add_status_widgets(items: Iterable[Tuple[QWidget, bool, int]]):
            status_bar = self.statusBar()
            for widget, is_permanent, _ in items:
                if is_permanent:
                    status_bar.addPermanentWidget(widget)
                else:
                    status_bar.addWidget(widget)

        _add_status_widgets(status_bar_left)

        # Add a spacer separating widgets (by just setting a high stretch)
        self.statusBar().addWidget(QWidget(), 9999)

        _add_status_widgets(status_bar_right)

        return stored_plugins

    @staticmethod
    def _load_plugins(env_var_path_key: str,
                      cmd_line_paths: Optional[List[str]],
                      shipped_plugin_path: str,
                      base_type: Type = CPlugin) -> Dict[str, Type]:

        all_plugin_paths = [str(Path(__file__).parent / 'plugins' / shipped_plugin_path)]

        extra_plugin_paths: str = ''
        try:
            extra_plugin_paths = os.environ[env_var_path_key]
        except KeyError:
            pass
        if extra_plugin_paths:
            all_plugin_paths = extra_plugin_paths.split(os.pathsep) + all_plugin_paths

        if cmd_line_paths:
            all_plugin_paths = cmd_line_paths + all_plugin_paths

        return load_plugins_from_path(locations=map(Path, all_plugin_paths),
                                      token='_plugin.py',
                                      base_type=base_type)

    @staticmethod
    def _read_widget_plugin_config(config: WindowPluginConfigTrie, plugin_id: str) -> Optional[Dict[str, str]]:
        try:
            return config.get_flat_config(plugin_id)
        except KeyError:
            logger.warning(f'Cannot read configuration for erroneous window plugin ID '
                           f'"{plugin_id}". The plugin will be initialized without configuration.')
        return None

    def __rbac_startup_login(self):
        # Done here and not in CApplication. See the reason at the caller location of this method
        from comrad import CApplication  # Import here to avoid circular dependency
        rbac = cast(CApplication, CApplication.instance()).rbac
        rbac.startup_login()


@modify_in_place
class _UiMainWindow(Ui_MainWindow, MonkeyPatchedClass):
    """
    Monkey-patched generated UI file class to replace labels as early as
    possible to not confuse the user with naming.
    """

    def setupUi(self, MainWindow: QMainWindow):
        try:
            self._overridden_members['setupUi'](self, MainWindow)
        except BaseException:  # noqa: B902
            # This catches built-in error produced by QtCore.QMetaObject.connectSlotsByName(MainWindow)
            # inside pydm_ui.py's setupUi. This error ("QtCore.QMetaObject.connectSlotsByName(MainWindow)")
            # is raised when MainWindow is monkey-patched, which is currently the only possible approach.
            # Fortunately, this call is the last in the setupUi file, so it can be assumed that execution
            # is allowed to continue after the exception. Also, there are no existing slots to connect at the
            # time of calling, so nothing is lost.
            pass

    def retranslateUi(self, MainWindow: QMainWindow):
        _translate = QCoreApplication.translate
        self._overridden_members['retranslateUi'](self, MainWindow)
        MainWindow.setWindowTitle(_translate('MainWindow', 'ComRAD Main Window'))
        self.actionAbout_PyDM.setText(_translate('MainWindow', 'About ComRAD'))

        nav_toggle = cast(QAction, self.navbar.toggleViewAction())
        nav_toggle.setText(_translate('MainWindow', 'Show Navigation Bar'))


class ToolbarSpacer(QWidget):
    """
    Special widget type that can be recognized from within QSS, to allow better dark-mode compatibility.
    """
    pass
