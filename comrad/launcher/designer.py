import os
from typing import Optional, List, Dict


def run_designer(ccda_env: str,
                 files: Optional[List[str]] = None,
                 online: bool = False,
                 use_inca: bool = True,
                 java_env: Optional[Dict[str, str]] = None,
                 server: bool = False,
                 client: Optional[int] = None,
                 resource_dir: Optional[str] = None,
                 enable_internal_props: bool = False,
                 blocking: bool = True):
    """
    Runs the Qt Designer with ComRAD modifications.

    Args:
        ccda_env: Environment flag to point CCDA to the correct CCDB instance
        files: files to be opened with Qt Designer (standard feature).
        online: Run Designer in online mode (receive live data). This is PyDM feature.
        use_inca: Run control system calls through InCA servers (only relevant when online is True)
        java_env: JVM flags to be passed to the control system libraries (only relevant when online is True)
        server: run as server (standard feature).
        client: port to use when run in the client mode (standard feature).
        resource_dir: custom resource directory (standard feature).
        enable_internal_props: enable internal dynamic properties (standard feature).
        blocking: wait for the Designer to close before returning from the method.

    Returns:
        CompletedProcess instance returned from subprocess.run()
    """
    import comrad.designer
    path_to_plugins = os.path.abspath(os.path.dirname(comrad.designer.__file__))
    env = {
        'PYQTDESIGNERPATH': path_to_plugins,
        'QT_DESIGNER_RAD_EXTRAS': '1',
        'QT_DESIGNER_RAD_CCDA': ccda_env,
    }

    if online:
        env['PYDM_DESIGNER_ONLINE'] = '1'
        env['QT_DESIGNER_RAD_INCA'] = str(int(use_inca))
        if java_env:
            env['QT_DESIGNER_RAD_JVM'] = ';'.join((f'{key}:{value}' for key, value in java_env.items()))

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

    env = dict(os.environ, **env)

    import subprocess
    if blocking:
        try:
            return subprocess.run(args=cmd, shell=False, env=env, check=True)
        except subprocess.CalledProcessError as e:
            exit(e.returncode)
    else:
        _ = subprocess.Popen(args=cmd, shell=False, env=env)
