from typing import Dict, Optional
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


def get_japc_support_envs() -> Dict[str, str]:
    """Environment variables necessary for PyDM operating with JAPC support."""
    return {
        'PYDM_DEFAULT_PROTOCOL': COMRAD_DEFAULT_PROTOCOL,
        'PYDM_DATA_PLUGINS_PATH': comrad_asset('data'),
    }
