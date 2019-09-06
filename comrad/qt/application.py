import os
import logging
from typing import Optional, List, Dict, Iterable, Type, Union, cast
from qtpy.QtWidgets import QAction, QMenu, QSpacerItem, QSizePolicy, QWidget, QHBoxLayout
from qtpy.QtCore import Qt, QObject
from pydm.application import PyDMApplication
from pydm.main_window import PyDMMainWindow
from pydm.pydm_ui import Ui_MainWindow
from comrad.utils import icon
from .frame_plugins import load_plugins_from_path
from .plugin import CToolbarActionPlugin, CActionPlugin, CToolbarWidgetPlugin, CToolbarPlugin, CToolbarPluginPosition


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
        self._load_toolbar_plugins(nav_bar_plugin_path)
        # TODO: Add exit menu item

    def _load_toolbar_plugins(self, extras: Optional[str]):
        all_plugin_paths = os.path.join(os.path.dirname(__file__), 'toolbar')

        if extras:
            all_plugin_paths = f'{extras}:{all_plugin_paths}'

        extra_plugin_paths: str = ''
        try:
            extra_plugin_paths = os.environ['COMRAD_TOOLBAR_PLUGIN_PATH']
        except KeyError:
            pass
        if extra_plugin_paths:
            all_plugin_paths = f'{extra_plugin_paths}:{all_plugin_paths}'

        locations = all_plugin_paths.split(':')

        toolbar_plugins: Dict[str, Type] = load_plugins_from_path(locations=locations,
                                                                  token='_plugin.py',
                                                                  base_type=CToolbarPlugin)
        if toolbar_plugins:
            ui: Ui_MainWindow = self.main_window.ui
            ui.navbar.addSeparator()

            toolbar_actions: List[QAction] = []
            toolbar_left: List[Union[QAction, QWidget]] = []  # Items preceding spacer
            toolbar_right: List[Union[QAction, QWidget]] = []  # Items succeeding spacer

            for plugin_type in toolbar_plugins.values():
                if issubclass(plugin_type, CActionPlugin):
                    plugin: CToolbarActionPlugin = plugin_type()
                    item = CAction(self.main_window, plugin=plugin)
                    toolbar_actions.append(item)
                else:
                    plugin: CToolbarWidgetPlugin = plugin_type()
                    item = plugin.create_widget()

                (toolbar_left if cast(CToolbarPlugin, plugin).position == CToolbarPluginPosition.LEFT
                 else toolbar_right).append(item)

            if toolbar_actions:
                self._add_plugins_menu(plugins=toolbar_actions, submenu='Toolbar')

            def _add_to_nav_bar(item: Union[QWidget, QAction]):
                if isinstance(item, QWidget):
                    ui.navbar.addWidget(item)
                elif isinstance(item, QAction):
                    ui.navbar.addAction(item)

            for item in toolbar_left:
                _add_to_nav_bar(item)

            # Add spacer to compress toolbar items when possible
            spacer = QWidget()
            layout = QHBoxLayout()
            spacer.setLayout(layout)
            layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
            ui.navbar.addWidget(spacer)

            for item in toolbar_right:
                _add_to_nav_bar(item)

    def _add_plugins_menu(self, plugins: Iterable[QAction], submenu: str):

        if self._plugins_menu is None:
            logger.debug('Adding plugins menu "Plugins"')
            self._plugins_menu = self.main_window.ui.menubar.addMenu('Plugins')

        menu: QMenu
        try:
            menu = next((a for a in self._plugins_menu.actions() if a.text() == submenu))
        except StopIteration:
            logger.debug(f'Adding plugins submenu "Plugins->{submenu}"')
            menu = self._plugins_menu.addMenu(submenu)

        menu.addActions(plugins)


class CAction(QAction):

    def __init__(self, parent: Optional[QObject], *args, plugin: CActionPlugin, **kwargs):
        super().__init__(parent, *args, **kwargs)
        # To keep the plugin object alive
        self._plugin = plugin

        self.setShortcutContext(Qt.ApplicationShortcut)
        if plugin.shortcut is not None:
            self.setShortcut(plugin.shortcut)
        if plugin.icon is not None:
            if isinstance(parent, PyDMMainWindow):
                main_window: PyDMMainWindow = parent
                self.setIcon(main_window.iconFont.icon(plugin.icon))
        self.triggered.connect(plugin.triggered)
        self.setText(plugin.title())
