import os
import logging
import types
import importlib
import importlib.util
import importlib.machinery
from pathlib import Path
from typing import List, Optional, cast, Tuple, Dict, Any
from comrad import CRbaStartupLoginPolicy
from comrad.app.plugins.toolbar import rbac_plugin


logger = logging.getLogger(__name__)


SUPPORTED_EXT = ['.py', '.ui', '.json', '.qss']

_CONFIG_FILE = '__init__.py'
_CURR_DIR: Path = Path(__file__).parent.absolute()


def find_runnable() -> List[Path]:
    """
    Crawls the examples folder trying to locate subdirectories that can be runnable examples.

    A runnable example is any subdirectory that has ``__init__.py`` file inside.
    The crawling is done recursively, but subdirectories of runnable examples are not crawled
    because they might contain code that is not supposed to be top-level examples.

    Returns:
        list of absolute paths to runnable examples.
    """
    excludes = {'_', '.'}
    example_paths: List[Path] = []
    for root, dirs, files in os.walk(_CURR_DIR):
        root_path = Path(root)
        logger.debug(f'Entering {root_path}')
        is_exec = _CONFIG_FILE in files
        if root_path != _CURR_DIR and is_exec:
            example_paths.append(root_path)
            logger.debug(f'Example {root_path} is executable. Will stop here.')
            dirs[:] = []  # Do not go deeper, as it might simply contain submodules
        else:
            dirs[:] = [d for d in dirs if d[0] not in excludes]
            logger.debug(f'Will crawl child dirs: {dirs}')

    logger.debug('Located examples in dirs:\n{paths}'.format(paths='\n'.join(map(str, example_paths))))
    return example_paths


def module(basedir: Path, name: str) -> Optional[types.ModuleType]:
    """
    Resolves the Python module from the directory of the example.

    Args:
        basedir: absolute path to the example.
        name: name of the example to be set for the module.

    Returns:
        Python module or None if failed to load.
    """
    if not basedir.is_dir():
        logger.warning(f'Cannot display example from {basedir} - not a directory')
        return None

    config = basedir / _CONFIG_FILE
    if not config.exists() or not config.is_file():
        logger.warning(f'Cannot display example from {basedir} - cannot find entry point')
        return None

    spec: Optional[importlib.machinery.ModuleSpec] = importlib.util.spec_from_file_location(name=name, location=config)
    if spec is None:
        logger.warning(f'Cannot import example from {basedir} - cannot find module spec')
        return None
    mod: types.ModuleType = importlib.util.module_from_spec(spec)
    loader = cast(importlib.machinery.SourceFileLoader, spec.loader)
    try:
        loader.exec_module(mod)
    except ImportError as ex:
        logger.warning(f'Cannot import example from {basedir}: {str(ex)}')
        return None
    return mod


def read(module: types.ModuleType, basedir: Path) -> Tuple[str, str, str, Optional[str], Optional[List[str]]]:
    """
    Read details of the example bundle, such as:

      * title
      * description
      * entrypoint file
      * filename with PAPC simulated device
      * extra launch arguments

    Args:
        module: Handle of the Python module
        basedir: Path to the directory containing example files

    Returns:
        Tuple of the aforementioned properties.

    Raises:
        AttributeError: When configuration of the example is incomplete
    """
    example_fgen: Optional[str]
    try:
        example_entrypoint: str = module.entrypoint  # type: ignore
        example_title: str = module.title  # type: ignore
        example_description: str = module.description  # type: ignore
    except AttributeError as ex:
        raise AttributeError(f'Cannot display example - config file is incomplete: {str(ex)}')
    try:
        fgen_name = module.japc_generator  # type: ignore
    except AttributeError:
        fgen_name = None

    example_args: Optional[List[str]]

    def expand_args(arg: str) -> str:
        import re
        return re.sub(pattern=r'^~example', repl=str(basedir), string=arg)

    try:
        example_args = list(map(expand_args, module.launch_arguments))  # type: ignore
    except AttributeError:
        example_args = None

    example_fgen = f'{_module_id(basedir)}.{fgen_name}' if fgen_name else None

    return example_title, example_description, example_entrypoint, example_fgen, example_args


def get_files(basedir: Path) -> List[Path]:
    """
    Retrieves files associated with the example.

    Args:
        basedir: Path to the directory containing example files

    Returns:
        List of the files belonging to the example.
    """
    bundle_files: List[Path] = []

    def is_file_allowed(file: str) -> bool:
        ext = Path(file).suffix
        return ext in SUPPORTED_EXT

    for root, dirs, files in os.walk(basedir):
        root_path = Path(root)
        try:
            dirs.remove('__pycache__')
        except ValueError:
            pass
        if root_path == basedir:
            files.remove(_CONFIG_FILE)
        files = cast(List[str], filter(is_file_allowed, files))
        bundle_files.extend(root_path / f for f in files)

    return bundle_files


def make_cmd(entrypoint: str,
             example_path: Path,
             japc_generator: Optional[str],
             extra_args: Optional[List[str]] = None) -> Tuple[List[str], Dict[str, Any]]:
    """
    Prepares the arguments and environment variables to be passed into :func:`subprocess.run` or
    :class:`suprocess.Popen`.

    Args:
        entrypoint: name of the main file of the application.
        example_path: Path to the directory containing example files.
        japc_generator: Name of the file that contains PAPC simulated device.
        extra_args: Optional arguments to use when launching the example.

    Returns:
        Tuple of command line arguments and environment variable dictionary similar to :attr:`os.environ`.
    """
    # We must run it as an external process, because event loop is already running
    file_path = example_path / entrypoint
    args: List[str] = ['comrad', 'run']

    if extra_args is not None:
        for arg in extra_args:
            _append_arg(args, arg)
    if '--log-level' not in args:
        # Mirror current log level to the child app (e.g. when running in DEBUG, also launch example in DEBUG)
        _append_arg(args, '--log-level')
        _append_arg(args, logging.getLevelName(logging.getLogger().level))
    if '--hide-log-console' not in args:
        # Disable log console in examples to not create cognitive overhead in already cramped UI
        _append_arg(args, '--hide-log-console')
    _disable_implicit_plugin(args, plugin_id=rbac_plugin.RbaToolbarPlugin.plugin_id)
    _append_arg(args, str(file_path))
    logger.debug(f'Launching app with args: {args}')
    env = dict(os.environ,
               PYJAPC_SIMULATION_INIT=(japc_generator or ''),
               COMRAD_STARTUP_LOGIN_POLICY=CRbaStartupLoginPolicy.NO_LOGIN.name)
    python_path = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = f'{_CURR_DIR}:{python_path}'
    return args, env


def _append_arg(args: List[str], arg: str):
    """Appends args safely, taking in account multiple values arguments and '--' terminator.

    Args:
        args: Argument list.
        arg: New argument.
    """
    if arg.startswith('--') and args[-1] == '--':
        args.pop()
    args.append(arg)


def _disable_implicit_plugin(input_args: List[str], plugin_id: str):
    """
    Disables the plugin for the examples run, that might be enabled by default.
    It will not touch the plugin if it is involved in the example (mentioned in the launch arguments)
    in any way.
    """
    disable_plugins_first_idx: Optional[int] = None
    disable_plugins_last_idx: Optional[int] = None
    disable_plugins_list: Optional[List[str]] = None
    for idx, arg in enumerate(input_args):
        if arg in ['--enable-plugins', '--disable-plugins', '--nav-bar-order']:
            plugin_ids = []
            plugin_index = idx + 1
            while True:
                try:
                    next_plugin = input_args[plugin_index]
                except IndexError:
                    break
                if next_plugin.startswith('--'):
                    break
                plugin_index += 1
                plugin_ids.append(next_plugin)
            if not plugin_ids:
                continue
            if plugin_id in plugin_ids:
                return  # Do not modify args, given plugin is explicitly participating in the example
            if arg == '--disable-plugins':
                disable_plugins_first_idx = idx + 1
                disable_plugins_last_idx = plugin_index
                disable_plugins_list = plugin_ids
    if (disable_plugins_first_idx is not None and disable_plugins_last_idx is not None
            and disable_plugins_list is not None):
        disable_plugins_list.append(plugin_id)
        input_args[disable_plugins_first_idx:disable_plugins_last_idx] = disable_plugins_list
    else:
        _append_arg(input_args, '--disable-plugins')
        _append_arg(input_args, plugin_id)
        _append_arg(input_args, '--')


def _module_id(basedir: Path) -> str:
    """
    Constructs the absolute module identifier.

    Because we are importing via importlib, the resulting identifier will be relative and will not
    include paths to the examples module itself.

    Args:
        basedir: absolute path to the module

    Returns:
        absolute identifier.
    """
    # Removes trailing '.__main__'
    abs_mod_path: List[str] = __loader__.name.split('.')  # type: ignore
    del abs_mod_path[-1]
    rel_path = basedir.relative_to(_CURR_DIR)
    abs_mod_path.extend(rel_path.parts)
    return '.'.join(abs_mod_path)
