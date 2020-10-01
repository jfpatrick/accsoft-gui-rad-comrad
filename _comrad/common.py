import os
from typing import Dict, Optional, List
from pathlib import Path
from .comrad_info import COMRAD_DEFAULT_PROTOCOL


def comrad_asset(file: str) -> str:
    """
    Locates a file inside main comrad package.

    Args:
        file: Filename.

    Returns:
        Absolute path to the file.

    Raises:
        RuntimeError: If main "comrad" package cannot be found.
    """
    import importlib.util
    import importlib.machinery
    # Locate the package without importing it to avoid parasitic logic run on import
    spec: Optional[importlib.machinery.ModuleSpec] = importlib.util.find_spec('comrad')
    if not spec or not spec.origin:
        raise RuntimeError('Cannot locate "comrad" package in the system. '
                           'Have you been manually deleting site-packages subdirectories? Please reinstall comrad!')
    return str(Path(spec.origin).parent.absolute() / file)


def get_japc_support_envs(extra_data_plugin_paths: Optional[List[str]]) -> Dict[str, str]:
    """
    Environment variables necessary for PyDM operating with JAPC support.

    Args:
        cli_var: Paths for custom data plugins passed via CLI.
    """
    data_plugin_path = comrad_asset('data')
    extra_paths = assemble_extra_data_plugin_paths(extra_data_plugin_paths)
    if extra_paths:
        data_plugin_path = os.pathsep.join([data_plugin_path, extra_paths])

    return {
        'PYDM_DEFAULT_PROTOCOL': COMRAD_DEFAULT_PROTOCOL,
        'PYDM_DATA_PLUGINS_PATH': data_plugin_path,
    }


def assemble_extra_plugin_paths(env_name: str, cli_var: Optional[List[str]] = None) -> Optional[str]:
    res: List[str] = cli_var or []
    env_path = os.environ.get(env_name)
    if env_path and isinstance(env_path, str):
        # Add plugins passed via environment variables
        res.append(env_path)
    if not res:
        return None
    return os.pathsep.join(res)


def assemble_extra_data_plugin_paths(cli_var: Optional[List[str]] = None) -> Optional[str]:
    """
    Joins the paths passed via CLI interface (``--extra-data-plugin-path``) with the ones found
    in environment variable ``COMRAD_DATA_PLUGIN_PATH``.

    Args:
        cli_var: Paths passed via CLI.

    Returns:
        Path (separated by ``:`` in POSIX) with concatenated paths.
    """
    # Add plugins passed as "--extra-data-plugin-path" argument in CLI
    return assemble_extra_plugin_paths('COMRAD_DATA_PLUGIN_PATH', cli_var)
