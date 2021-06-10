#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# Feature to enable argcomplete when it looks into this file
import logging
import argparse
import functools
import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List, Iterable, Any, Set, cast
from argparse import RawDescriptionHelpFormatter, ArgumentParser, Namespace
from pathlib import Path
from argcomplete import autocomplete
from argparse_profiles import ProfileParser
from accwidgets.qt import exec_app_interruptable
from .comrad_info import COMRAD_DESCRIPTION, COMRAD_VERSION, get_versions_info
from .log_config import install_logger_level
from .common import get_japc_support_envs, comrad_asset
from .package import generate_pyproject_with_spec, make_requirement_safe, Requirement, parse_maintainer_info


def create_args_parser(deployed_pkg_name: Optional[str] = None) -> Tuple[ArgumentParser, bool]:
    """
    Build ComRAD application arguments.

    Args:
        deployed_pkg_name: Name of the application when it's deployed with "comrad package". This replaces a number
                           of configurations from standard "comrad" (which is used at the development time) to
                           deployed package name that is more relevant for the user.

    Returns:
        Tuple of arguments parser and flag if the lazy version resolution should be done.
    """
    logo = """

   ██████╗ ██████╗ ███╗   ███╗██████╗  █████╗ ██████╗
  ██╔════╝██╔═══██╗████╗ ████║██╔══██╗██╔══██╗██╔══██╗
  ██║     ██║   ██║██╔████╔██║██████╔╝███████║██║  ██║
  ██║     ██║   ██║██║╚██╔╝██║██╔══██╗██╔══██║██║  ██║
  ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║  ██║██║  ██║██████╔╝
   ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝
    """
    common_parser_args: Dict[str, Any] = {
        'add_help': False,  # Will be added manually (with consistent formatting)
        'formatter_class': RawDescriptionHelpFormatter,
    }

    parser = ArgumentParser(description=logo + '\n\n' + COMRAD_DESCRIPTION, **common_parser_args)

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

    subparsers = parser.add_subparsers(dest='cmd', parser_class=_EmptyLoadSaveActionProfileParser)
    app_parser_args = {} if deployed_pkg_name is None else {'prog': f'python -m {deployed_pkg_name}'}
    app_parser = cast(_EmptyLoadSaveActionProfileParser,
                      subparsers.add_parser('run',
                                            help='Launch main ComRAD application.',
                                            description='  This command launches the client application with ComRAD environment.\n'
                                                        '  It is the starting point for runtime applications that have been\n'
                                                        '  developed with ComRAD tools and rely on control system marshalling\n'
                                                        '  logic and other conveniences provided by ComRAD.',
                                            **app_parser_args,
                                            **common_parser_args))
    subparsers._parser_class = ArgumentParser  # Make sure all other subcommands are of regular type
    app_parser._parser_class = ArgumentParser  # Make sure all subparsers of "comrad run" are of regular type
    _run_subcommand(parser=app_parser, deployed_pkg_name=deployed_pkg_name)

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

    package_parser = subparsers.add_parser('package',
                                           help='Convert ComRAD project into an installable Python package.',
                                           description='  This command creates a pip-compatible pyproject.toml file,\n'
                                                       '  enabling standard tools, such as "pip install" or\n'
                                                       '  "pip wheel", to be run over the directory, to produce a\n'
                                                       '  wheel or sdist. Resulting package can be later deployed to\n'
                                                       '  operational environment using "acc-py app deploy" command\n'
                                                       '  from Acc-Py dev-tools.',
                                           **common_parser_args)
    _package_subcommand(package_parser)

    return parser, use_lazy_version


@dataclass
class DeployedArgs:
    """
    This class separates arguments for the usage in deployed applications, that can be properly
    supplied into-the argparse-profiles. There are currently 3 levels of argument priorities:

    - Lowest: Baked-in (implicit) application arguments
    - Medium: Arguments embedded into the profile
    - Highest: Arguments supplied by the user.

    To parse them properly (also to save them into a profile and load them from the profile), care is needed
    during parsing, therefore we keep them decoupled.
    """

    baked_in: List[str]
    """Baked-in (implicit) application arguments."""

    user: List[str]
    """Arguments supplied by the user."""

    entrypoint: str
    """Main application file."""

    command: str
    """Subcommand to run."""


def parse_args(parser: ArgumentParser, args: Optional[DeployedArgs] = None) -> Namespace:
    """
    Parse arguments using a given parser.

    Args:
        parser: That acts as an entrypoint for parsing the arguments.
        args: Packaged applications can use these arguments, to properly merge them by priority, depending on the
              source of the argument.

    Returns:
        Parsed arguments as a namespace.
    """
    args_to_parse: Optional[List[str]] = None
    # Namespace represents compiled implicit arguments that will have
    # lower priority than the final_args
    pre_parsed_namespace: Optional[Namespace] = None
    if args:
        pre_parsed_args = [args.command] + args.baked_in + [_DELIM, args.entrypoint]
        # This pre-parses (before second final parsing in the end of the
        # function to produce a lower-priority namespace)
        pre_parsed_namespace = parser.parse_args(pre_parsed_args)
        # There can be only a single '--' in the arguments. We use it by default in the end to
        # safely terminate in the end, but if it happened to be used in the middle by the user
        # we have to fallback and hope that user did not put array in the end without the '--' termination
        positionals = [args.entrypoint] if _DELIM in args.user else [_DELIM, args.entrypoint]
        # Baked-in args must be supplied here even with pre-parsing for the final namespace to be complete
        args_to_parse = [args.command] + args.baked_in + args.user + positionals

    return parser.parse_args(args=args_to_parse, namespace=pre_parsed_namespace)


_DELIM = '--'


def process_args(args: Namespace, parser: ArgumentParser, use_lazy_version: bool = False):
    if use_lazy_version and args.version:
        _run_version(parser)
        return

    install_logger_level(vars(args).get('log_level'))
    if args.cmd == 'examples':
        # Importing it here to have a chance to setup root logger before
        from _comrad_examples.browser import run_browser as run_examples_browser
        run_examples_browser(args)
    else:
        if args.cmd == 'run' and _run_comrad(args):
            return
        elif args.cmd == 'designer' and _run_designer(args):
            return
        elif args.cmd == 'package' and _package_app(args):
            return
        parser.print_help()


def run():
    """Run ComRAD application and parse command-line arguments."""
    try:
        parser, use_lazy_version = create_args_parser()

        # If run for auto-completion discovery, execution will stop here
        autocomplete(parser)
        args = parse_args(parser)

        process_args(args=args,
                     parser=parser,
                     use_lazy_version=use_lazy_version)
    except KeyboardInterrupt:
        pass


class _EmptyLoadSaveActionProfileParser(ProfileParser):
    """
    Subclass to allow defining load and save actions of argparse-profiles manually in the desired place.
    """

    def create_parser_args(self, parser_action_group_name: str):
        # Do nothing in this method, because we'll add the actions manually in the right place,
        # where it fits compared to other action groups.
        pass


def _install_help(parser: ArgumentParser):
    parser.add_argument('-h', '--help',
                        action='help',
                        help='Show this help message and exit.')


def _install_controls_arguments(parser: ArgumentParser):
    parser.add_argument('-s', '--selector',
                        metavar='SELECTOR',
                        help='Default selector for the window. Selectors allow specifying the timing user, so the data '
                             'is received only when specific timing user is being played. ComRAD window will have a '
                             'selector affecting all of its widgets. This selector can be changed via "PLS" toolbar '
                             'item. When omitted, no selector will be used.',
                        default=None)
    parser.add_argument('--rbac-token',
                        metavar='abcdef123456',
                        help='Base64-serialized RBAC token to automatically obtain authenticated state. If provided, '
                             'this will override default policy of "login by location at startup".',
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


def _install_debug_arguments(parser: ArgumentParser):
    parser.add_argument('--log-level',
                        help='Configure level of log display (default: INFO).',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default=None)


def _run_subcommand(parser: _EmptyLoadSaveActionProfileParser, deployed_pkg_name: Optional[str]):
    parser._argparse_profiles_default_path = Path(deployed_pkg_name or 'comrad')
    required_group = parser.add_argument_group('Required arguments')
    required_group.add_argument('display_file',
                                metavar='FILE',
                                help='Main client program (can be a Qt Designer or a Python file).')

    launch_group = parser.add_argument_group('Launch configuration')
    profile_params = launch_group.add_mutually_exclusive_group()
    parser._argparse_profiles_load_action = profile_params.add_argument('--use-profile',
                                                                        default=argparse.SUPPRESS,
                                                                        type=str,
                                                                        required=False,
                                                                        action='append',
                                                                        dest='argparse_profiles_load_action',
                                                                        help='Name of the profile file to load additional flags from.',
                                                                        metavar='PROFILE_NAME')
    parser._argparse_profiles_save_action = profile_params.add_argument('--save-to-profile',
                                                                        default=argparse.SUPPRESS,
                                                                        type=str,
                                                                        required=False,
                                                                        dest='argparse_profiles_save_action',
                                                                        help='Name of the profile file to save the current parameters to. '
                                                                             'Passing this flag will not allow the application to start.',
                                                                        metavar='PROFILE_NAME')

    display_group = parser.add_argument_group('Display configuration')
    display_group.add_argument('display_args',
                               help='Any extra arguments to be passed to the main CDisplay subclass (only '
                                    'when user supplies *.py file as FILE with CDisplay subclass, "args" keyword is '
                                    'populated with this list). This may be useful to pass arguments from '
                                    'CRelatedDisplayButton.',
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

    appearance_group.add_argument('--hide-menu-bar',
                                  action='store_true',
                                  help='Launch ComRAD with the menu bar hidden.')
    appearance_group.add_argument('--hide-log-console',
                                  action='store_true',
                                  help='Launch ComRAD with the log console hidden.')
    appearance_group.add_argument('--hide-status-bar',
                                  action='store_true',
                                  help='Launch ComRAD with the status bar hidden.')
    appearance_group.add_argument('--hide-nav-bar',
                                  action='store_true',
                                  help='Launch ComRAD with the navigation bar hidden.')
    appearance_group.add_argument('--nav-bar-style',
                                  help='Configure the style of the navigation bar (default: vstack). '
                                       'Choises: icon (icons only); text (text only); vstack (text under icons); '
                                       'hstack: (text beside icons).',
                                  choices=['icon', 'text', 'vstack', 'hstack'],
                                  default='vstack')
    appearance_group.add_argument('--nav-bar-position',
                                  help='Configure the positioning of the navigation bar (default: top).',
                                  choices=['top', 'left'],
                                  default='top')

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

    controls_group = cast(ArgumentParser, parser.add_argument_group('Control system configuration'))
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
    plugin_group.add_argument('--window-plugin-config',
                              metavar='key=value',
                              help='Specify configuration for window plugins (status bar, menu bar or navigation bar). '
                                   "Key of each config value should start with plugins's ID, followed by the "
                                   'configuration key name, e.g. comrad.pls.show_bar=1 will trigger the "show_bar" '
                                   'option on the plugin with ID "comrad.pls". For the bundled comrad plugins, the '
                                   'following keys are available: comrad.pls.show_sel, comrad.pls.show_bar, '
                                   'comrad.pls.supercycle, comrad.pls.show_domain, comrad.pls.show_time, '
                                   'comrad.pls.show_start, comrad.pls.show_user, comrad.pls.show_lsa, '
                                   'comrad.pls.show_tz, comrad.pls.heartbeat, comrad.pls.microseconds, comrad.pls.utc.',
                              nargs=argparse.ONE_OR_MORE)
    debug_group = cast(ArgumentParser, parser.add_argument_group('Debugging'))
    _install_debug_arguments(debug_group)
    debug_group.add_argument('--perf-mon',
                             action='store_true',
                             help='Enable performance monitoring, and print CPU usage to the terminal.')

    info_group = cast(ArgumentParser, parser.add_argument_group('User information'))
    _install_help(info_group)


def _examples_subcommand(parser: ArgumentParser):
    _install_debug_arguments(parser)
    _install_help(parser)


def __designer_subcommand(parser: ArgumentParser):
    comrad_group = cast(ArgumentParser, parser.add_argument_group('ComRAD arguments'))
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

    qt_group = cast(ArgumentParser, parser.add_argument_group('Standard Qt Designer arguments'))
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


def _run_comrad(args: Namespace) -> bool:
    logger = logging.getLogger('')

    # This has to sit here, because other os.environ settings MUST be before comrad or pydm import
    environment = {
        'PYDM_TOOLS_PATH': comrad_asset('tools'),
        **get_japc_support_envs(args.extra_data_plugin_path),
    }

    try:
        ccda_endpoint, java_env, os_env = _parse_control_env(args)
    except EnvironmentError as e:
        logger.exception(str(e))
        return False

    environment.update(os_env)
    environment['PYCCDA_HOST'] = ccda_endpoint

    logger.debug('Configured additional environment:\n'
                 '{env_dict}'.format(env_dict='\n'.join([f'{k}={v}' for k, v in environment.items()])))

    for k, v in environment.items():
        os.environ[k] = v

    # Importing stuff here and not in the beginning of the file to setup the root logger first.
    from comrad.app.application import CApplication, CRbaStartupLoginPolicy
    from pydm.utilities.macro import parse_macro_string
    macros = parse_macro_string(args.macro) if args.macro is not None else None

    stylesheet: Optional[str] = (comrad_asset('dark.qss') if args.dark_mode or os.environ.get('COMRAD_DARK_MODE_ENABLED', False)
                                 else args.stylesheet)

    # TODO: This is a short-term hotfix. We need a more secure solution
    # Work around behavior change in Python 3.7 (https://docs.python.org/3/whatsnew/3.7.html#changes-in-python-behavior),
    # last bullet point mentioning sys.path
    # See https://issues.cern.ch/browse/ACCPY-731 for details
    if sys.version_info.major > 3 or (sys.version_info.major == 3 and sys.version_info.minor >= 7):
        sys.path.append(os.getcwd())

    startup_policy: Optional[CRbaStartupLoginPolicy]
    try:
        startup_policy = CRbaStartupLoginPolicy[os.environ.get('COMRAD_STARTUP_LOGIN_POLICY', '')]
    except KeyError:
        startup_policy = None

    app = CApplication(ui_file=args.display_file,
                       command_line_args=args.display_args,
                       use_inca=not args.no_inca,
                       ccda_endpoint=ccda_endpoint,
                       cmw_env=args.cmw_env,
                       default_selector=args.selector or None,
                       rbac_token=args.rbac_token,
                       startup_login_policy=startup_policy,
                       java_env=java_env,
                       perf_mon=args.perf_mon,
                       hide_nav_bar=args.hide_nav_bar,
                       hide_menu_bar=args.hide_menu_bar,
                       hide_log_console=args.hide_log_console,
                       hide_status_bar=args.hide_status_bar,
                       fullscreen=args.fullscreen,
                       read_only=args.read_only,
                       macros=macros,
                       data_plugin_paths=args.extra_data_plugin_path,
                       nav_bar_plugin_path=args.nav_plugin_path,
                       status_bar_plugin_path=args.status_plugin_path,
                       menu_bar_plugin_path=args.menu_plugin_path,
                       toolbar_order=args.nav_bar_order,
                       toolbar_style=args.nav_bar_style,
                       toolbar_position=args.nav_bar_position,
                       window_plugin_config=args.window_plugin_config,
                       plugin_blacklist=args.disable_plugins,
                       plugin_whitelist=args.enable_plugins,
                       stylesheet_path=stylesheet)
    # install_asyncio_event_loop(app)
    sys.exit(exec_app_interruptable(app))
    return True


def _run_designer(args: Namespace) -> bool:

    try:
        ccda_endpoint, java_env, os_env = _parse_control_env(args)
    except EnvironmentError as e:
        logging.getLogger('').exception(str(e))
        return False

    os.environ.update(os_env)

    if args.rbac_token is not None:
        # To be picked up by PyJapc, if activated inside Designer, because CApplication won't exist and will
        # not automatically propagate it to pyrbac login.
        os.environ['RBAC_TOKEN_SERIALIZED'] = args.rbac_token

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


def _run_version(parser: ArgumentParser):
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


def _parse_control_env(args: Namespace) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    from .comrad_info import CCDA_MAP
    cmw_env: str = args.cmw_env
    try:
        ccda_endpoint = CCDA_MAP[cmw_env]
    except KeyError:
        raise EnvironmentError(f'Invalid CMW environment specified: {cmw_env}')

    java_env: Optional[List[str]] = args.java_env
    jvm_flags = {}
    os_env = {}
    if java_env:
        for arg in java_env:
            name, val = tuple(arg.split('='))
            if name.startswith('rbac.'):
                raise EnvironmentError(f'RBAC-related JVM flags are forbidden. Use RBAC_* environment variables instead.')
            jvm_flags[name] = val
    if cmw_env not in ['PRO', 'PRO2']:
        if cmw_env.endswith('2'):
            cmw_env = cmw_env[:-1]
        jvm_flags['cmw.directory.env'] = cmw_env
        os_env['RBAC_ENV'] = cmw_env

    return ccda_endpoint, jvm_flags, os_env


def _package_subcommand(parser: ArgumentParser):
    _install_help(parser)

    parser.add_argument('--no-interactive',
                        help='Run packaging in a non-interactive mode.',
                        action='store_false',
                        dest='interactive',
                        default=True)
    _install_debug_arguments(parser)
    parser.add_argument('display_file',
                        metavar='FILE',
                        help='Application entrypoint: Qt Designer (*.ui) or Python (*.py) file.')

    result_group = parser.add_argument_group('Final product details')
    result_group.add_argument('--name',
                              help='Name of the final product (must comply to Python package naming conventions).')
    result_group.add_argument('--version',
                              help='Version of the final product (use PEP-440 compatible version string).')
    result_group.add_argument('--description',
                              help='Summary of the final product.')
    maintainer_group = result_group.add_mutually_exclusive_group()
    maintainer_group.add_argument('--maintainer',
                                  help='Name and/or email of the package maintainer. This can be formatted in '
                                       'either ways: "John Smith <john.smith@cern.ch>"; or "John Smith"; '
                                       'or john.smith@cern.ch.')
    maintainer_group.add_argument('--force-phonebook',
                                  help='Enforce resolution of maintainer info from the phonebook, '
                                       'overriding any cached maintainer info (only applicable in interactive mode).',
                                  action='store_true')
    req_group = result_group.add_mutually_exclusive_group()
    req_group.add_argument('--requirements',
                           help='List dependencies of your final product that should be installed with it.',
                           action='append',
                           default=[],
                           nargs=argparse.ZERO_OR_MORE)
    req_group.add_argument('--requirements-file',
                           help='Path to the requirements.txt listing final product dependencies.')


def _package_app(args: Namespace) -> bool:
    entrypoint = Path(args.display_file)

    reqs: Iterable[str]
    if args.requirements_file:
        requirements_file = Path(args.requirements_file)
        with requirements_file.open('r+t') as f:
            reqs = filter(lambda r: not r.strip().startswith('#'), f.readlines())
    elif args.requirements:
        reqs = args.requirements[0]
    else:
        reqs = []

    req_objects = map(functools.partial(make_requirement_safe, error='Requirement will be ignored.'), reqs)
    install_requires: Optional[Set[Requirement]] = {r for r in req_objects if r is not None} or None

    enforced_spec_attrs = {
        'name': args.name,
        'version': args.version,
    }

    if args.description:
        enforced_spec_attrs['description'] = args.description
    maintainer_name, maintainer_email = parse_maintainer_info(args.maintainer)
    if maintainer_name is not None:
        enforced_spec_attrs['maintainer'] = maintainer_name
    if maintainer_email is not None:
        enforced_spec_attrs['maintainer_email'] = maintainer_email

    generate_pyproject_with_spec(entrypoint=entrypoint,
                                 cli_install_requires=install_requires,
                                 cli_other_spec_props=enforced_spec_attrs,
                                 force_phonebook=args.force_phonebook,
                                 interactive=args.interactive)

    return True
