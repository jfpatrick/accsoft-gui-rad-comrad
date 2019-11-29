#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# Feature to enable argcomplete when it looks into this file
import argparse
import argcomplete
import logging
import os
import sys
from typing import Optional, Iterable, cast, Tuple, Dict, List
from pydm.utilities.macro import parse_macro_string
from comrad import __version__
from comrad.qt.application import CApplication
from comrad.utils import ccda_map
from comrad.examples.__main__ import populate_parser as populate_examples_parser, run_browser as run_examples_browser


logging.basicConfig()


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
    if args.cmd == 'examples':
        run_examples_browser(args)
    else:
        if args.cmd == 'run':
            _run_comrad(args) or parser.print_usage()
        elif args.cmd == 'designer':
            _run_designer(args) or parser.print_usage()
        else:
            parser.print_help()


_PKG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _relative(file: str) -> str:
    return os.path.join(_PKG_PATH, file)


def _install_help(parser: argparse.ArgumentParser):
    parser.add_argument('-h', '--help',
                        action='help',
                        help='Show this help message and exit.')


def _install_controls_arguments(parser: argparse.ArgumentParser):
    parser.add_argument('--no-inca',
                        action='store_true',
                        help='Do not use InCA server middleware and connect directly to devices. By default JAPC '
                             'connection will use a set of known InCA servers.')
    parser.add_argument('--cmw-env',
                        help='Configure environment for CMW directory service, RBAC and CCDB. (default: PRO)'
                             ' - PRO: stable production service; uses CCDB PRO schema; - TEST: stable test/testbed '
                             'service for integration/acceptance/system testing to be used by external clients; '
                             'uses CCDB INT schema; - INT: unstable integration service for internal CMW '
                             'integration testing used by the CMW team only; uses CCDB INT schema; - DEV: '
                             'Development environment. Uses CCDB DEV schema. The environments with suffix \'2\' are'
                             ' similar to original ones but use alternative CCDB endpoints.',
                         choices=['PRO', 'TEST', 'INT', 'DEV', 'PRO2', 'TEST2', 'INT2', 'DEV2'],
                         default='PRO')
    parser.add_argument('--java-env',
                        help='Custom JVM flags to be passed for JVM-dependent control libraries. Note, all '
                             'Java-based libraries will reuse the same JVM, therefore these variables will '
                             'affect all of them.',
                        metavar="key=value",
                        nargs=argparse.ONE_OR_MORE)


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

    controls_group = parser.add_argument_group('Control system configuration')
    _install_controls_arguments(controls_group)

    plugin_group = parser.add_argument_group('Extensions')
    plugin_group.add_argument('--enable-plugins',
                              metavar="'ID,...'",
                              help='Specify plugins that are disabled by default but should be enabled in '
                                   'this instance. Plugins can be built-in or custom ones that are '
                                   'visible to the application (make sure to specify --nav-plugin-path or '
                                   'COMRAD_TOOLBAR_PLUGIN_PATH for any custom plugins). The order must be a comma-'
                                   'separated string with plugin IDs. For built-in items use following identifiers:'
                                   ' - RBAC dialog button: comrad.rbac'
                                   ''
                                   "Example usage: --enable-plugins 'comrad.rbac'",
                              default=None)
    plugin_group.add_argument('--disable-plugins',
                              metavar="'ID,...'",
                              help='Specify plugins that are enabled by default but should be disabled in '
                                   'this instance. Plugins can be built-in or custom ones that are '
                                   'visible to the application (make sure to specify --nav-plugin-path or '
                                   'COMRAD_TOOLBAR_PLUGIN_PATH for any custom plugins). The order must be a comma-'
                                   'separated string with plugin IDs. For built-in items use following identifiers:'
                                   ' - RBAC dialog button: comrad.rbac'
                                   ''
                                   "Example usage: --disable-plugins 'comrad.rbac'",
                              default=None)
    plugin_group.add_argument('--status-plugin-path',
                              metavar='PATH',
                              help='Specify the full path to a directory containing status bar ComRAD plugins.',
                              default=None)
    plugin_group.add_argument('--menu-plugin-path',
                              metavar='PATH',
                              help='Specify the full path to a directory containing menu bar ComRAD plugins.',
                              default=None)
    plugin_group.add_argument('--nav-plugin-path',
                              metavar='PATH',
                              help='Specify the full path to a directory containing toolbar ComRAD plugins.',
                              default=None)
    plugin_group.add_argument('--nav-bar-order',
                              metavar="'ID,...'",
                              help='Specify the order of items to appear in the navigation bar. Plugins must be '
                                   'visible to the application (make sure to specify --nav-plugin-path or '
                                   'COMRAD_TOOLBAR_PLUGIN_PATH for any custom plugins). The order must be a comma-'
                                   'separated string with plugin IDs. For native items, use following identifiers:'
                                   ' - "Back" button: comrad.back'
                                   ' - "Forward" button: comrad.fwd'
                                   ' - "Home" button: comrad.home'
                                   ' - Toolbar separator: comrad.sep'
                                   ' - Toolbar empty space: comrad.spacer'
                                   ' - RBAC dialog button: comrad.rbac'
                                   ''
                                   "Example usage: --nav-bar-order 'comrad.home,comrad.sep,comrad.spacer,comrad.rbac'",
                              default=None)

    debug_group = parser.add_argument_group('Debugging')
    debug_group.add_argument('--log-level',
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
                              nargs=argparse.ZERO_OR_MORE,
                              default=None)
    comrad_group.add_argument('--online',
                              action='store_true',
                              help='Launch ComRAD Designer displaying live data from the control system.')
    _install_help(comrad_group)
    _install_controls_arguments(comrad_group)

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


def _run_comrad(args: argparse.Namespace) -> bool:

    macros = parse_macro_string(args.macro) if args.macro is not None else None

    if args.log_level:
        level_name: str = args.log_level.upper()
        level: Optional[int]
        logger = logging.getLogger('')
        try:
            level = getattr(logging, level_name)
        except AttributeError as ex:
            logger.exception(f'Invalid logging level specified ("{level_name}"): {str(ex)}')
            level = None

        if level:
            # Redefine the level of the root logger
            logger.setLevel(level)

    try:
        _, java_env = _parse_control_env(args)
    except EnvironmentError as e:
        logger.exception(str(e))
        return False

    order: Optional[Iterable[str]] = None
    if args.nav_bar_order:
        order = cast(str, args.nav_bar_order).split(',')

    whitelist: Optional[Iterable[str]] = None
    if args.enable_plugins:
        whitelist = cast(str, args.enable_plugins).split(',')

    blacklist: Optional[Iterable[str]] = None
    if args.disable_plugins:
        blacklist = cast(str, args.disable_plugins).split(',')

    stylesheet: Optional[str] = _relative('dark.qss') if args.dark_mode else args.stylesheet

    os.environ['PYDM_DATA_PLUGINS_PATH'] = _relative('data')
    os.environ['PYDM_TOOLS_PATH'] = _relative('tools')
    os.environ['PYDM_DEFAULT_PROTOCOL'] = 'japc'

    app = CApplication(ui_file=args.display_file,
                       command_line_args=args.display_args,
                       use_inca=not args.no_inca,
                       java_env=java_env,
                       perfmon=args.perfmon,
                       hide_nav_bar=args.hide_nav_bar,
                       hide_menu_bar=args.hide_menu_bar,
                       hide_status_bar=args.hide_status_bar,
                       fullscreen=args.fullscreen,
                       read_only=args.read_only,
                       macros=macros,
                       nav_bar_plugin_path=args.nav_plugin_path,
                       status_bar_plugin_path=args.status_plugin_path,
                       menu_bar_plugin_path=args.menu_plugin_path,
                       toolbar_order=order,
                       plugin_blacklist=blacklist,
                       plugin_whitelist=whitelist,
                       stylesheet_path=stylesheet)
    sys.exit(app.exec_())
    return True


def _run_designer(args: argparse.Namespace) -> bool:

    try:
        ccda_endpoint, java_env = _parse_control_env(args)
    except EnvironmentError as e:
        print(str(e))
        return False

    from .designer import run_designer
    run_designer(files=args.files,
                 ccda_env=ccda_endpoint,
                 java_env=java_env,
                 use_inca=not args.no_inca,
                 online=args.online,
                 server=args.server,
                 client=args.client,
                 resource_dir=args.resourcedir,
                 enable_internal_props=args.enableinternaldynamicproperties)
    return True


def _parse_control_env(args: argparse.Namespace) -> Tuple[str, Dict[str, str]]:

    cmw_env: str = args.cmw_env
    try:
        ccda_endpoint = ccda_map[cmw_env]
    except KeyError:
        raise EnvironmentError(f'Invalid CMW environment specified: {cmw_env}')

    java_env: Optional[List[str]] = args.java_env
    jvm_flags = {}
    if java_env:
        for arg in java_env:
            name, val = tuple(arg.split('='))
            jvm_flags[name] = val
    if cmw_env not in ['PRO', 'PRO2']:
        if cmw_env.endswith('2'):
            cmw_env = cmw_env[:-1]
        jvm_flags['cmw.directory.env'] = cmw_env
        jvm_flags['rbac.env'] = cmw_env

    return ccda_endpoint, jvm_flags