import argparse
import logging
import os
import sys
from typing import Optional
from pydm.application import PyDMApplication
from pydm.utilities.macro import parse_macro_string
from comrad import __version__


logging.basicConfig()
logger = logging.getLogger('')


_PKG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _relative(file: str) -> str:
    return os.path.join(_PKG_PATH, file)


def run():
    """Run ComRAD application and parse command-line arguments."""
    logo = """

   ██████╗ ██████╗ ███╗   ███╗██████╗  █████╗ ██████╗
  ██╔════╝██╔═══██╗████╗ ████║██╔══██╗██╔══██╗██╔══██╗
  ██║     ██║   ██║██╔████╔██║██████╔╝███████║██║  ██║
  ██║     ██║   ██║██║╚██╔╝██║██╔══██╗██╔══██║██║  ██║
  ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║  ██║██║  ██║██████╔╝
   ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝
    """
    parser = argparse.ArgumentParser(description=f'{logo}\n\nComRAD (CO Multi-purpose Rapid Application Development environment)',
                                     add_help=False,  # Will be added manually to a different group
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    required_group = parser.add_argument_group('Required arguments')
    required_group.add_argument('display_file',
                                metavar='FILE',
                                help='Main client program (can be a Qt Designer or a Python file).')

    display_group = parser.add_argument_group('Display configuration')
    display_group.add_argument('display_args',
                               help='Any extra arguments to be passed to the ComRAD client application '
                                    '(which is a QApplication subclass).',
                               metavar='...',
                               nargs=argparse.REMAINDER,
                               default=None)
    display_group.add_argument('-m', '--macro',
                               help=('Specify macro replacements to use, in JSON object format. '
                                     'Reminder: JSON requires double quotes for strings, '
                                     'so you should wrap this whole argument in single quotes. '
                                     'Example: -m \'{"sector": "LI25", "facility": "LCLS"}\' '
                                     '--or-- specify macro replacements as KEY=value pairs '
                                     'using a comma as delimiter  If you want to uses spaces '
                                     'after the delimiters or around the = signs, '
                                     'wrap the entire set with quotes. '
                                     'Example: -m "sector = LI25, facility=LCLS".'))
    display_group.add_argument('--read-only',
                               action='store_true',
                               help='Launch ComRAD in a read-only mode.')

    # comrad_group.add_argument('--examples',  # TODO: WIll need to import parser from examples and add it as subcommand here
    #                           action='store_true',
    #                           help='Instead of launching main application, ')

    appearance_group = parser.add_argument_group('Appearance configuration')

    appearance_group.add_argument('--hide-nav-bar',
                                  action='store_true',
                                  help='Launch ComRAD with the navigation bar hidden.')
    appearance_group.add_argument('--hide-menu-bar',
                                  action='store_true',
                                  help='Launch ComRAD with the menu bar hidden.')
    appearance_group.add_argument('--hide-status-bar',
                                  action='store_true',
                                  help='Launch ComRAD with the status bar hidden.')
    appearance_group.add_argument('--fullscreen',
                                  action='store_true',
                                  help='Launch ComRAD in full screen mode.')
    appearance_group.add_argument('--stylesheet',
                                  metavar='QSS',
                                  help='Specify the full path to a *.qss file, which can be used to customize '
                                       'the appearance of ComRAD and Qt widgets.',
                                  default=None)
    appearance_group.add_argument('--dark-mode',
                                  action='store_true',
                                  help='Use predefined stylesheet with the dark theme for the application. '
                                       '(This option will override --stylesheet flag).')

    debug_group = parser.add_argument_group('Debugging')
    debug_group.add_argument('--log_level',
                             help='Configure level of log display (default: INFO).',
                             choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                             default='INFO')
    debug_group.add_argument('--perfmon',
                             action='store_true',
                             help='Enable performance monitoring, and print CPU usage to the terminal.')

    info_group = parser.add_argument_group('User information')
    info_group.add_argument('-V', '--version',
                            action='version',
                            version=f'ComRAD {__version__}',
                            help="Show ComRAD's version number and exit.")
    info_group.add_argument('-h', '--help',
                            action='help',
                            help='Show this help message and exit.')

    args = parser.parse_args()
    macros = parse_macro_string(args.macro) if args.macro is not None else None

    if args.log_level:
        logger.setLevel(args.log_level)

    stylesheet: Optional[str] = _relative('dark.qss') if args.dark_mode else args.stylesheet

    os.environ['PYDM_DATA_PLUGINS_PATH'] = _relative('data')
    os.environ['PYDM_TOOLS_PATH'] = _relative('tools')
    os.environ['PYDM_DEFAULT_PROTOCOL'] = 'japc'

    app = PyDMApplication(ui_file=args.display_file,
                          command_line_args=args.display_args,
                          perfmon=args.perfmon,
                          hide_nav_bar=args.hide_nav_bar,
                          hide_menu_bar=args.hide_menu_bar,
                          hide_status_bar=args.hide_status_bar,
                          fullscreen=args.fullscreen,
                          read_only=args.read_only,
                          macros=macros,
                          stylesheet_path=stylesheet)
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
