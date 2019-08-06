import os
import sys
from typing import Any, Dict, List


__all__ = [
    'designer',
    'pydm',
]


_PKG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_DARK_FLAG = '--dark-mode'


def _run_cmd(cmd: str, env: Dict[str, Any], args: List[str] = sys.argv, **kwargs: Dict[str, Any]):
    """
    Run a command with the given environment variables.

    Args:
        cmd: Name of the executable
        env: Dictionary with environment variables
        args: Command-line arguments to read
        **kwargs: Any additional arguments to be passed to subprocess.run()

    Returns:
        CompletedProcess instance returned from subprocess.run()
    """
    import subprocess
    sys_args = list(args)
    sys_args.pop(0)
    args = [cmd] + sys_args
    try:
        return subprocess.run(args=args, shell=False, env=dict(os.environ, **env), check=True, **kwargs)
    except subprocess.CalledProcessError as e:
        exit(e.returncode)


def designer():
    """Runs Qt Designer with the environment preset to activate RAD features and locate extra plugins."""
    import comrad.designer
    path_to_plugins = os.path.abspath(os.path.dirname(comrad.designer.__file__))
    _run_cmd(cmd='designer', env=dict(PYQTDESIGNERPATH=path_to_plugins, QT_DESIGNER_RAD_EXTRAS='1'))


def pydm():
    """Runs 'pydm' command with the environment preset to locate plugins and tools from ComRAD package."""
    envs = dict(PYDM_DATA_PLUGINS_PATH=os.path.join(_PKG_PATH, 'data'),
                PYDM_DEFAULT_PROTOCOL='japc',
                PYDM_TOOLS_PATH=os.path.join(_PKG_PATH, 'tools'))

    args = sys.argv
    if _DARK_FLAG in args:
        envs['PYDM_STYLESHEET'] = os.path.join(_PKG_PATH, 'dark.qss')
        args.remove(_DARK_FLAG)

    # The available environment variables are listed in the docs:
    # http://slaclab.github.io/pydm/configuration.html
    _run_cmd(cmd='pydm', env=envs, args=args)
