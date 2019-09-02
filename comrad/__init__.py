"""
ComRAD framework
CO Multi-purpose Rapid Application Development

This framework integrates several tools to be used for developing applications in Python.
It allows for easy integration between CO control system and Qt GUI framework to produce
Operational GUI applications without much hassle.
"""
# flake8: noqa: E401,E403
from .qt.pydm_api import *
from .qt.pydm_widgets import *
from .qt.cern_widgets import *


__author__ = 'Ivan Sinkarenko <ivan.sinkarenko@cern.ch>'

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
