from typing import NamedTuple, Optional

COMRAD_DESCRIPTION = \
    f'''  ComRAD (CO Multi-purpose Rapid Application Development environment)

  ComRAD framework seeks to streamline development of operational
  applications for operators of CERN accelerators and machine design
  experts. It offers a set of tools to develop and run applications
  without the need to be an expert in software engineering domain.'''


class AccPyEnv(NamedTuple):
    """Tuple that accumulates versions of the Acc-py environment."""
    py: str
    pyqt: str


class Versions(NamedTuple):
    """Tuple that accumulates versions of the most important dependencies."""
    comrad: str
    widgets: str
    cmmn_build: str
    pyjapc: str
    pydm: str
    np: str
    pg: str
    python: str
    pyqt: str
    qt: str
    accpy: Optional[AccPyEnv] = None


def get_versions_info() -> Versions:
    import numpy as np
    import pydm
    import pyqtgraph as pg
    import comrad
    import sys
    import pathlib
    import os
    import pyjapc
    import cmmnbuild_dep_manager
    from qtpy.QtCore import __version__ as pyqt_ver, qVersion

    python_ver = ".".join([str(v) for v in sys.version_info[0:3]])
    qt_ver = qVersion()
    np_ver = np.__version__
    pydm_ver = pydm.__version__
    pg_ver = pg.__version__
    comrad_ver = comrad.__version__
    pyjapc_ver = pyjapc.__version__
    cmmn_ver = cmmnbuild_dep_manager.__version__
    # TODO: Make widgets version when ready
    widgets_ver = '0.1.0' #accsoft_gui_pyqt_widgets.__version__
    accpy: Optional[AccPyEnv] = None

    if 'ACC_PY_PREFIX' in os.environ and 'ACC_PYQT_PREFIX' in os.environ:
        accpy_ver = pathlib.Path(os.environ['ACC_PY_PREFIX']).name
        accpyqt_ver = pathlib.Path(os.environ['ACC_PYQT_PREFIX']).name
        accpy = AccPyEnv(py=accpy_ver, pyqt=accpyqt_ver)

    return Versions(comrad=comrad_ver,
                    widgets=widgets_ver,
                    cmmn_build=cmmn_ver,
                    pyjapc=pyjapc_ver,
                    pydm=pydm_ver,
                    np=np_ver,
                    pg=pg_ver,
                    python=python_ver,
                    pyqt=pyqt_ver,
                    qt=qt_ver,
                    accpy=accpy)