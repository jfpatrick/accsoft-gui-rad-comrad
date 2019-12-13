"""
ComRAD framework
CO Multi-purpose Rapid Application Development

This framework integrates several tools to be used for developing applications in Python.
It allows for easy integration between CO control system and Qt GUI framework to produce
Operational GUI applications without much hassle.
"""
# flake8: noqa: E401,E403
from _comrad.comrad_info import COMRAD_AUTHOR as __author__, COMRAD_VERSION as __version__
from .qt.pydm_api import *
from .qt.pydm_widgets import *
from .qt.cern_widgets import *
from .qt.widgets import *
from .qt.application import *
