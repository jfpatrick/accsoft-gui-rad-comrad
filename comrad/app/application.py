import os
import logging
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Iterable, Union
from qtpy.QtWidgets import QMenu, QMessageBox
from .main_window import CMainWindow  # This has to be above PyDMApplication to ensure monkey-patching
from pydm.application import PyDMApplication
from pydm.utilities import path_info, which
from pydm.data_plugins import is_read_only
from comrad.icons import icon
from comrad.rbac import CRBACState
from comrad.app.plugins import CToolbarID


logger = logging.getLogger(__name__)


_APP_NAME = 'ComRAD'


class CApplication(PyDMApplication):

    def __init__(self,
                 ccda_endpoint: str,
                 ui_file: Optional[str] = None,
                 command_line_args: Optional[List[str]] = None,
                 display_args: Optional[List[str]] = None,
                 use_inca: bool = True,
                 default_selector: Optional[str] = None,
                 cmw_env: Optional[str] = None,
                 java_env: Optional[Dict[str, str]] = None,
                 perf_mon: bool = False,
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
            default_selector: Default selector to use for window context at the startup.
            cmw_env: Original CMW environment. While it is not directly used in this instance, instead relying on
                ``java_env`` and ``ccda_endpoint``, it will be passed to any child ComRAD processes.
            java_env: JVM flags to be passed to the control system libraries.
            perf_mon: Whether or not to enable performance monitoring using ``psutil``.
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
            toolbar_order: List of IDs of toolbar items in order in which they must appear left-to-right.
            plugin_whitelist: List of plugin IDs that have to be enabled even if they are disabled by default.
            plugin_blacklist: List of plugin IDs that have to be disabled even if they are enabled by default.
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
                         perfmon=perf_mon,
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

        # Useful for sub-processes
        self._stylesheet_path = stylesheet_path
        self._nav_bar_plugin_path = nav_bar_plugin_path
        self._status_bar_plugin_path = status_bar_plugin_path
        self._menu_bar_plugin_path = menu_bar_plugin_path
        self._toolbar_order = toolbar_order
        self._plugin_whitelist = plugin_whitelist
        self._plugin_blacklist = plugin_blacklist
        self._perf_mon = perf_mon

        order: Optional[List[Union[str, CToolbarID]]] = None
        if toolbar_order is not None:

            def _convert(identifier: Union[str, CToolbarID]) -> Union[str, CToolbarID]:
                try:
                    return CToolbarID(identifier)
                except ValueError:
                    # Not a valid CToolbarID identifier
                    return identifier

            order = list(map(_convert, toolbar_order))
        self.main_window.load_window_plugins(nav_bar_plugin_path=nav_bar_plugin_path,
                                             status_bar_plugin_path=status_bar_plugin_path,
                                             menu_bar_plugin_path=menu_bar_plugin_path,
                                             toolbar_order=order,
                                             plugin_whitelist=plugin_whitelist,
                                             plugin_blacklist=plugin_blacklist)
        if default_selector:
            self.main_window.window_context.selector = default_selector

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
        if self._perf_mon:
            args.append('--perf-mon')
        if self._stylesheet_path:
            args.extend(['--stylesheet', self._stylesheet_path])
        if macros is not None:
            args.extend(['-m', json.dumps(macros)])
        if not self.use_inca:
            args.append('--no-inca')
        if self.main_window.window_context.selector:
            args.extend(['--selector', self.main_window.window_context.selector])
        if self.jvm_flags:
            java_env = '--java-env'
            for key, flag_val in self.jvm_flags:
                java_env += f' {key}={flag_val}'
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
