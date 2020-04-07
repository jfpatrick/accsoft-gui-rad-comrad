"""
All graphical widgets that can be either dragged onto a form in ComRAD
Designer or embedded into GUI programmatically.

Usually widgets get exposed in main :mod:`comrad` module directly, so instead of

>>> from comrad.widgets.indicators import CLabel

you can do

>>> from comrad import CLabel

"""
# flake8: noqa: E401,E403
from . import widget
