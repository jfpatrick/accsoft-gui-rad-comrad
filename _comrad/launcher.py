#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# Feature to enable argcomplete when it looks into this file
import logging
import argparse
import argcomplete
import os
import sys
from typing import Optional, Tuple, Dict, List, Iterable
from .comrad_info import COMRAD_DESCRIPTION, COMRAD_VERSION, get_versions_info
from .log_config import install_logger_level
from .common import get_japc_support_envs, comrad_asset


# Allow smooth exit on Ctrl+C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


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

    parser = argparse.ArgumentParser(description=logo + '\n\n' + COMRAD_DESCRIPTION, **common_parser_args)

    parse_private_fn = getattr(parser, '_print_message', None)
    use_lazy_version = parse_private_fn and callable(parse_private_fn)
    if use_lazy_version:
        # This will use our custom command with delayed version resolution to avoid early imports of the
        # dependencies that may break order of defining custom environment variables
        parser.add_argument('-V', '--version',
                            action='store_true',
                            help="Show ComRAD's version number and exit.")
    else:
        # If the above assumption is incorrect, fallback to the simplest version
        parser.add_argument('-V', '--version',
                            action='version',
                            version=COMRAD_VERSION,
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
    if use_lazy_version and args.version:
        _run_version(parser)
        return

    install_logger_level(vars(args).get('log_level'))
    if args.cmd == 'examples':
        # Importing it here to have a chance to setup root logger before
        from _comrad_examples.browser import run_browser as run_examples_browser
        run_examples_browser(args)
    else:
        if args.cmd == 'run':
            _run_comrad(args) or parser.print_usage()
        elif args.cmd == 'designer':
            _run_designer(args) or parser.print_usage()
        else:
            parser.print_help()


def _install_help(parser: argparse._ActionsContainer):
    parser.add_argument('-h', '--help',
                        action='help',
                        help='Show this help message and exit.')


def _install_controls_arguments(parser: argparse._ActionsContainer):
    parser.add_argument('-s', '--selector',
                        metavar='SELECTOR',
                        help='Default selector for the window. Selectors allow specifying the timing user, so the data '
                             'is received only when specific timing user is being played. ComRAD window will have a '
                             'selector affecting all of its widgets. This selector can be changed via "PLS" toolbar '
                             'item. When omitted, no selector will be used.',
                        default=None)
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
                             "Development environment. Uses CCDB DEV schema. The environments with suffix '2' are "
                             'similar to original ones but use alternative CCDB endpoints.',
                        choices=['PRO', 'TEST', 'INT', 'DEV', 'PRO2', 'TEST2', 'INT2', 'DEV2'],
                        default='PRO')
    parser.add_argument('--java-env',
                        help='Custom JVM flags to be passed for JVM-dependent control libraries. Note, all '
                             'Java-based libraries will reuse the same JVM, therefore these variables will '
                             'affect all of them.',
                        metavar='key=value',
                        nargs=argparse.ONE_OR_MORE)
    parser.add_argument('--extra-data-plugin-path',
                        help='Path to user-defined ComRAD data plugins for alternative control-system communications. '
                             'It is joined together with standard ComRAD data handlers (e.g. JAPC) as well as plugins '
                             'found in paths defined by COMRAD_DATA_PLUGIN_PATH.',
                        metavar='PATH',
                        nargs=argparse.ZERO_OR_MORE,
                        default=None)


def _install_debug_arguments(parser: argparse._ActionsContainer):
    parser.add_argument('--log-level',
                        help='Configure level of log display (default: INFO).',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO')


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
                              metavar='ID',
                              help='Specify plugins that are disabled by default but should be enabled in '
                                   'this instance. Plugins can be built-in or custom ones that are '
                                   'visible to the application (make sure to specify --nav-plugin-path or '
                                   'COMRAD_TOOLBAR_PLUGIN_PATH for any custom plugins). For built-in items '
                                   'use following identifiers:'
                                   ' - RBAC dialog button: comrad.rbac'
                                   ' '
                                   'Example usage: --enable-plugins comrad.rbac org.example.my-plugin',
                              nargs=argparse.ONE_OR_MORE)
    plugin_group.add_argument('--disable-plugins',
                              metavar='ID',
                              help='Specify plugins that are enabled by default but should be disabled in '
                                   'this instance. Plugins can be built-in or custom ones that are '
                                   'visible to the application (make sure to specify --nav-plugin-path or '
                                   'COMRAD_TOOLBAR_PLUGIN_PATH for any custom plugins). For built-in items '
                                   'use following identifiers:'
                                   ' - RBAC dialog button: comrad.rbac'
                                   ' '
                                   'Example usage: --disable-plugins comrad.rbac org.example.my-plugin',
                              nargs=argparse.ONE_OR_MORE)
    plugin_group.add_argument('--status-plugin-path',
                              metavar='PATH',
                              help='Specify the full path(s) to location(s) containing status bar ComRAD plugins.',
                              nargs=argparse.ONE_OR_MORE)
    plugin_group.add_argument('--menu-plugin-path',
                              metavar='PATH',
                              help='Specify the full path(s) to location(s) containing menu bar ComRAD plugins.',
                              nargs=argparse.ONE_OR_MORE)
    plugin_group.add_argument('--nav-plugin-path',
                              metavar='PATH',
                              help='Specify the full path(s) to location(s) containing toolbar ComRAD plugins.',
                              nargs=argparse.ONE_OR_MORE)
    plugin_group.add_argument('--nav-bar-order',
                              metavar='ID',
                              help='Specify the order of items to appear in the navigation bar. Plugins must be '
                                   'visible to the application (make sure to specify --nav-plugin-path or '
                                   'COMRAD_TOOLBAR_PLUGIN_PATH for any custom plugins). For native items, use '
                                   'following identifiers:'
                                   ' - "Back" button: comrad.back'
                                   ' - "Forward" button: comrad.fwd'
                                   ' - "Home" button: comrad.home'
                                   ' - Toolbar separator: comrad.sep'
                                   ' - Toolbar empty space: comrad.spacer'
                                   ' - RBAC dialog button: comrad.rbac'
                                   ' '
                                   'Example usage: --nav-bar-order comrad.home comrad.sep comrad.spacer comrad.rbac',
                              nargs=argparse.ONE_OR_MORE)

    debug_group = parser.add_argument_group('Debugging')
    _install_debug_arguments(debug_group)
    debug_group.add_argument('--perf-mon',
                             action='store_true',
                             help='Enable performance monitoring, and print CPU usage to the terminal.')

    info_group = parser.add_argument_group('User information')
    _install_help(info_group)


def _examples_subcommand(parser: argparse.ArgumentParser):
    _install_debug_arguments(parser)
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
    _install_debug_arguments(comrad_group)
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

    environment = {
        'PYDM_TOOLS_PATH': comrad_asset('tools'),
        **get_japc_support_envs(args.extra_data_plugin_path),
    }

    for k, v in environment.items():
        os.environ[k] = v

    logger = logging.getLogger('')
    logger.debug('Configured additional environment:\n'
                 '{env_dict}'.format(env_dict='\n'.join([f'{k}={v}' for k, v in environment.items()])))

    # Importing stuff here and not in the beginning of the file to setup the root logger first.
    from comrad.app.application import CApplication
    from pydm.utilities.macro import parse_macro_string
    macros = parse_macro_string(args.macro) if args.macro is not None else None

    try:
        ccda_endpoint, java_env = _parse_control_env(args)
    except EnvironmentError as e:
        logger.exception(str(e))
        return False

    # This has to sit here, because other os.environ settings MUST be before comrad or pydm import
    os.environ['PYCCDA_HOST'] = ccda_endpoint

    stylesheet: Optional[str] = comrad_asset('dark.qss') if args.dark_mode else args.stylesheet

    app = CApplication(ui_file=args.display_file,
                       command_line_args=args.display_args,
                       use_inca=not args.no_inca,
                       ccda_endpoint=ccda_endpoint,
                       cmw_env=args.cmw_env,
                       default_selector=args.selector or None,
                       java_env=java_env,
                       perf_mon=args.perf_mon,
                       hide_nav_bar=args.hide_nav_bar,
                       hide_menu_bar=args.hide_menu_bar,
                       hide_status_bar=args.hide_status_bar,
                       fullscreen=args.fullscreen,
                       read_only=args.read_only,
                       macros=macros,
                       data_plugin_paths=args.extra_data_plugin_path,
                       nav_bar_plugin_path=args.nav_plugin_path,
                       status_bar_plugin_path=args.status_plugin_path,
                       menu_bar_plugin_path=args.menu_plugin_path,
                       toolbar_order=args.nav_bar_order,
                       plugin_blacklist=args.disable_plugins,
                       plugin_whitelist=args.enable_plugins,
                       stylesheet_path=stylesheet)
    sys.exit(app.exec_())
    return True


def _run_designer(args: argparse.Namespace) -> bool:

    try:
        ccda_endpoint, java_env = _parse_control_env(args)
    except EnvironmentError as e:
        logging.getLogger('').exception(str(e))
        return False

    from .designer import run_designer
    run_designer(files=args.files,
                 ccda_env=ccda_endpoint,
                 java_env=java_env,
                 use_inca=not args.no_inca,
                 selector=args.selector or None,
                 online=args.online,
                 server=args.server,
                 client=args.client,
                 resource_dir=args.resourcedir,
                 log_level=args.log_level,
                 extra_data_plugin_paths=args.extra_data_plugin_path,
                 enable_internal_props=args.enableinternaldynamicproperties)
    return True


def _run_version(parser: argparse.ArgumentParser):
    versions = get_versions_info()
    version_str = f"""ComRAD {versions.comrad}

Based on:
---------
Acc-py Widgets v{versions.widgets}
PyJAPC v{versions.pyjapc}
Java Dependency Manager v{versions.cmmn_build}
PyDM v{versions.pydm}
NumPy v{versions.np}
PyQtGraph v{versions.pg}

Environment:
------------\n"""

    if versions.accpy:
        version_str += f'Acc-py PyQt {versions.accpy.pyqt} (PyQt v{versions.pyqt}, Qt v{versions.qt})\n' + \
                       f'Acc-py Python {versions.accpy.py} (Python v{versions.python})'
    else:
        version_str += f'PyQt v{versions.pyqt}\n' + \
                       f'Qt v{versions.qt}\n' + \
                       f'Python v{versions.python}'

    items: Iterable[str]

    from .common import assemble_extra_data_plugin_paths
    extra_plugin_paths = assemble_extra_data_plugin_paths()
    if extra_plugin_paths:
        version_str += '\n\nUser-defined ComRAD data plugin paths:'
        items = filter(None, extra_plugin_paths.split(os.pathsep))  # Filter out empty strings
        for p in items:
            version_str += f'\n * {p}'

    version_str += '\n\n'
    # This uses private API based on assumption that we checked when constructing the parser
    parser._print_message(version_str)


def _parse_control_env(args: argparse.Namespace) -> Tuple[str, Dict[str, str]]:
    from .comrad_info import CCDA_MAP
    cmw_env: str = args.cmw_env
    try:
        ccda_endpoint = CCDA_MAP[cmw_env]
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
