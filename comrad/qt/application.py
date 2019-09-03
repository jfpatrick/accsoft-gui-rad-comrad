from typing import Optional, List, Dict
from pydm.application import PyDMApplication
from comrad.utils import icon


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
        self.setWindowIcon(icon('app', file_path=__file__))
        self.main_window.setWindowTitle('ComRAD Main Window')
