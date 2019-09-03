#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# Feature to enable argcomplete when it looks into this file
import argparse
import argcomplete
import logging
import os
import sys
from typing import Optional
from pydm.utilities.macro import parse_macro_string
from comrad import __version__, CApplication
from comrad.examples.__main__ import populate_parser as populate_examples_parser, run_browser as run_examples_browser


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
    common_parser_args = {
        'add_help': False,  # Will be added manually (with consistent formatting)
        'formatter_class': argparse.RawDescriptionHelpFormatter,
    }
    parser = argparse.ArgumentParser(description=f'{logo}\n\n'
                                                 f'  ComRAD (CO Multi-purpose Rapid Application Development '
                                                 f'environment)\n\n'
                                                 f'  ComRAD framework seeks to streamline development of operational\n'
                                                 f'  applications for operators of CERN accelerators and machine design\n'
                                                 f'  experts. It offers a set of tools to develop and run applications\n'
                                                 f'  without the need to be an expert in software engineering domain.',
                                     **common_parser_args)

    parser.add_argument('-V', '--version',
                        action='version',
                        version=f'ComRAD {__version__}',
                        help="Show ComRAD's version number and exit.")
    _install_help(parser)

    subparsers = parser.add_subparsers(dest='cmd')
    app_parser = subparsers.add_parser('run',
                                       help='Launch main ComRAD application.',
                                       description='  This command launch the client application with ComRAD environment.\n'
                                                   '  It is the starting point for runtime applications that have been\n'
                                                   '  developed with ComRAD tools and rely on control system marshalling\n'
                                                   '  logic and other conveniences provided by ComRAD.',
                                       **common_parser_args)
    _run_subcommand(app_parser)

    designer_parser = subparsers.add_parser('designer',
                                            help='Launch ComRAD Designer.',
                                            description='  This command launches ComRAD Designer - a modified version\n'
                                                        '  of Qt Designer that can be used to develop ComRAD applications\n'
                                                        '  in a WYSIWYG (What-You-See-Is-What-You-Get) mode.',
                                            **common_parser_args)
    __designer_subcommand(designer_parser)

    examples_parser = subparsers.add_parser('examples',
                                            help='Launch ComRAD interactive examples browser.',
                                            description='  This command launches an interactive examples browser that\n'
                                                        '  you can use to get familiar with available widgets in ComRAD\n'
                                                        '  devtools and best practices.',
                                            **common_parser_args)
    _examples_subcommand(examples_parser)

    # If run for auto-completion discovery, execution will stop here
    argcomplete.autocomplete(parser)

    args = parser.parse_args()
    if args.cmd == 'run':
        _run_comrad(args)
    elif args.cmd == 'examples':
        run_examples_browser(args)
    elif args.cmd == 'designer':
        _run_designer(args)
    else:
        parser.print_help()


_PKG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _relative(file: str) -> str:
    return os.path.join(_PKG_PATH, file)


def _install_help(parser: argparse.ArgumentParser):
    parser.add_argument('-h', '--help',
                        action='help',
                        help='Show this help message and exit.')


def _run_subcommand(parser: argparse.ArgumentParser):
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
    _install_help(info_group)


def _examples_subcommand(parser: argparse.ArgumentParser):
    populate_examples_parser(parser)
    _install_help(parser)


def __designer_subcommand(parser: argparse.ArgumentParser):
    comrad_group = parser.add_argument_group('ComRAD arguments')
    comrad_group.add_argument('files',
                              help='Files to be opened in ComRAD designer.',
                              metavar='FILES',
                              nargs='*',
                              default=None)
    comrad_group.add_argument('--online',
                              action='store_true',
                              help='Launch ComRAD Designer displaying live data from the control system.')
    _install_help(comrad_group)

    qt_group = parser.add_argument_group('Standard Qt Designer arguments')
    qt_group.add_argument('--server',
                          action='store_true',
                          help='Launch Qt Designer in server mode.')
    qt_group.add_argument('--client',
                          metavar='PORT',
                          help='Launch Qt Designer in client mode.',
                          default=None)
    qt_group.add_argument('--resourcedir',
                          metavar='DIR',
                          help='Specify resource directory.',
                          default=None)
    qt_group.add_argument('--enableinternaldynamicproperties',
                          action='store_true',
                          help='Enable internal dynamic properties.')


logging.basicConfig()
logger = logging.getLogger('')


def _run_comrad(args: argparse.Namespace):
    macros = parse_macro_string(args.macro) if args.macro is not None else None

    if args.log_level:
        logger.setLevel(args.log_level)

    stylesheet: Optional[str] = _relative('dark.qss') if args.dark_mode else args.stylesheet

    os.environ['PYDM_DATA_PLUGINS_PATH'] = _relative('data')
    os.environ['PYDM_TOOLS_PATH'] = _relative('tools')
    os.environ['PYDM_DEFAULT_PROTOCOL'] = 'japc'

    app = CApplication(ui_file=args.display_file,
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


def _run_designer(args: argparse.Namespace):
    from .designer import run_designer
    run_designer(files=args.files,
                 online=args.online,
                 server=args.server,
                 client=args.client,
                 resource_dir=args.resourcedir,
                 enable_internal_props=args.enableinternaldynamicproperties)
