import sys
# You can also do type(qtpy.QtCore.QObject) to receive wrappertype and
# stay cross-platform, but I'm not sure what PySide would return
from PyQt5.sip import wrappertype


if sys.version_info[1] <= 6:
    # GenericMeta is based on ABCMeta, therefore we need only tthis
    from typing import GenericMeta
else:
    # Since Python 3.7, GenericMeta has been removed
    from abc import ABCMeta as GenericMeta


class GenericQObjectMeta(GenericMeta, wrappertype):
    """
    Metaclass for classes that want to subclass :class:`typing.Generic` class and are :class:`QObject` subclasses.
    """

    def __init__(self, *args, **kwargs):
        GenericMeta.__init__(self, *args, **kwargs)

        # Explicitly call the wrappertype initializer as ABCMeta/GenericMeta doesn't.
        wrappertype.__init__(self, *args, **kwargs)
