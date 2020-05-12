from typing import NamedTuple, Optional, Dict
from ._version import get_versions as get_comrad_versions


COMRAD_DESCRIPTION = \
    """  ComRAD (CO Multi-purpose Rapid Application Development environment)

  ComRAD framework seeks to streamline development of operational
  applications for operators of CERN accelerators and machine design
  experts. It offers a set of tools to develop and run applications
  without the need to be an expert in software engineering domain."""
"""Description of ComRAD framework to be presented in help messages and about dialogs."""


COMRAD_AUTHOR = 'Ivan Sinkarenko <ivan.sinkarenko@cern.ch>'
"""Support contact information to be presented in help messages and about dialogs."""


COMRAD_VERSION = get_comrad_versions()['version']
"""ComRAD framework version to be presented in help messages and about dialogs."""


COMRAD_DEFAULT_PROTOCOL = 'japc'
"""Default protocol that is used for the control system connections that do not specify it explicitly."""


class AccPyEnv(NamedTuple):
    """Tuple that accumulates versions of the Acc-py environment."""
    py: str  # Version of Python distribution.
    pyqt: str  # Version of Python distribution.


class Versions(NamedTuple):
    """Tuple that accumulates versions of the most important dependencies."""
    comrad: str  # Version of ComRAD framework.
    widgets: str  # Version of Acc-Py widget library.
    cmmn_build: str  # Version of cmmn_build_dep_manager
    jpype: str  # Version of JPype Java bindings
    pyjapc: str  # Version of PyJAPC library
    pydm: str  # Version of PyDM framework
    np: str  # Version of NumPy library
    pg: str  # Version of PyQtGraph library
    python: str  # Version of Python interpreter
    pyqt: str  # Version of PyQt bindings
    qt: str  # Version of Qt framework
    accpy: Optional[AccPyEnv] = None  # Acc-Py-related version


def get_versions_info() -> Versions:
    """
    Retrieve the versions of the framework and its dependencies.

    Returns:
        Versions tuple.
    """

    import sys
    import pathlib
    import os
    from cmmnbuild_dep_manager import __version__ as cmmn_ver
    from accwidgets import __version__ as widgets_ver
    from pyjapc import __version__ as pyjapc_ver
    from numpy import __version__ as np_ver
    from pyqtgraph import __version__ as pg_ver
    from pydm import __version__ as pydm_ver
    from jpype import __version__ as jpype_ver

    try:
        # Somehow qtpy imports only Qt version, but not PyQt, so we need to directly access PyQt5
        from PyQt5.QtCore import PYQT_VERSION_STR as pyqt_ver, QT_VERSION_STR as qt_ver
    except ImportError:
        import qtpy.QtCore
        try:
            qt_ver = qtpy.QtCore.__version__
        except ImportError:
            qt_ver = '???'
        pyqt_ver = '???'

    python_ver = '.'.join([str(v) for v in sys.version_info[0:3]])
    accpy: Optional[AccPyEnv] = None

    if 'ACC_PY_PREFIX' in os.environ and 'ACC_PYQT_PREFIX' in os.environ:
        accpy_ver = pathlib.Path(os.environ['ACC_PY_PREFIX']).name
        accpyqt_ver = pathlib.Path(os.environ['ACC_PYQT_PREFIX']).name
        accpy = AccPyEnv(py=accpy_ver, pyqt=accpyqt_ver)

    return Versions(comrad=COMRAD_VERSION,
                    widgets=widgets_ver,
                    cmmn_build=cmmn_ver,
                    pyjapc=pyjapc_ver,
                    pydm=pydm_ver,
                    jpype=jpype_ver,
                    np=np_ver,
                    pg=pg_ver,
                    python=python_ver,
                    pyqt=pyqt_ver,
                    qt=qt_ver,
                    accpy=accpy)


CCDA_MAP: Dict[str, str] = {
    'PRO': 'https://ccda.cern.ch:8900/api',
    'PRO2': 'https://ccda.cern.ch:8901/api',
    'TEST': 'https://ccda-test.cern.ch:8902/api',
    'TEST2': 'https://ccda-test.cern.ch:8903/api',
    'INT': 'https://ccda-int.cern.ch:8904/api',
    'INT2': 'https://ccda-int.cern.ch:8905/api',
    'DEV': 'https://ccda-dev.cern.ch:8906/api',
    'DEV2': 'https://ccda-dev.cern.ch:8907/api',
}
"""Mapping between predefined CMW environments and corresponding CCDA endpoints."""
