import os
from typing import Any, Dict


__all__ = [
    'designer',
    'pydm',
]


def _run_cmd(cmd: str, env: Dict[str, Any], **kwargs: Dict[str, Any]):
    """
    Run a command with the given environment variables.

    Args:
        cmd: Name of the executable
        env: Dictionary with environment variables
        **kwargs: Any additional arguments to be passed to subprocess.run()

    Returns:
        CompletedProcess instance returned from subprocess.run()
    """
    import subprocess
    import sys
    sys_args = list(sys.argv)
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
    import comrad.data
    import comrad.tools
    path_to_plugins = os.path.abspath(os.path.dirname(comrad.data.__file__))
    path_to_tools = os.path.abspath(os.path.dirname(comrad.tools.__file__))

    # The available environment variables are listed in the docs:
    # http://slaclab.github.io/pydm/configuration.html
    _run_cmd(cmd='pydm', env=dict(PYDM_DATA_PLUGINS_PATH=path_to_plugins,
                                  PYDM_DEFAULT_PROTOCOL='japc',
                                  PYDM_TOOLS_PATH=path_to_tools,
                                  ))
