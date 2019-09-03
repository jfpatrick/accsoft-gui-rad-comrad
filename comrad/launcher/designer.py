import os
from typing import Optional, List


def run_designer(files: Optional[List[str]] = None,
                 online: bool = False,
                 server: bool = False,
                 client: Optional[int] = None,
                 resource_dir: Optional[str] = None,
                 enable_internal_props: bool = False):
    """
    Runs the Qt Designer with ComRAD modifications.

    Args:
        files: files to be opened with Qt Designer (standard feature).
        online: Run Designer in online mode (receive live data). This is PyDM feature.
        server: run as server (standard feature).
        client: port to use when run in the client mode (standard feature).
        resource_dir: custom resource directory (standard feature).
        enable_internal_props: enable internal dynamic properties (standard feature).

    Returns:
        CompletedProcess instance returned from subprocess.run()
    """
    import comrad.designer
    path_to_plugins = os.path.abspath(os.path.dirname(comrad.designer.__file__))
    env = {'PYQTDESIGNERPATH': path_to_plugins,
           'QT_DESIGNER_RAD_EXTRAS': '1'}

    if online:
        env['PYDM_DESIGNER_ONLINE'] = '1'

    cmd: List[str] = ['designer']

    # Forward Qt Designer arguments
    if server:
        cmd.append('--server')
    if client is not None:
        cmd.append('--client')
        cmd.append(str(client))
    if resource_dir is not None:
        cmd.append('--resourcedir')
        cmd.append(resource_dir)
    if enable_internal_props:
        cmd.append('--enableinternaldynamicproperties')

    if files:
        cmd.extend(files)

    import subprocess
    try:
        return subprocess.run(args=cmd, shell=False, env=dict(os.environ, **env), check=True)
    except subprocess.CalledProcessError as e:
        exit(e.returncode)
