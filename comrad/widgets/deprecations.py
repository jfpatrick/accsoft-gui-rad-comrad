import logging
from types import MethodType
from typing import cast
from qtpy.QtWidgets import QWidget


logger = logging.getLogger(__name__)


def superclass_deprecated(method: MethodType):
    """
    Decorator to deprecate properties exposed to Qt Designer that are actually defined in dependencies outside of ComRAD.

    Args:
        method: Method to decorate.

    Returns:
        Wrapper method with decorated logic.
    """

    def _wrapper(self, *_, **__):
        from pydm.utilities import is_qt_designer
        if not is_qt_designer():
            from comrad.widgets.mixins import InitializedMixin
            if not isinstance(self, InitializedMixin):
                raise TypeError(f'This decorator is intended to be used with InitializedMixin. {type(self).__name__} is not recognized as one.')
            widget = cast(InitializedMixin, self)
            if not widget._widget_initialized:
                # Ignore setting properties in __init__, which may come from PyDM superclasses
                return
            name = cast(QWidget, self).objectName()
            if not name:
                name = f'unidentified {type(self).__name__}'
            logger.warning(f'{method.__name__} property is disabled in ComRAD (found in {name})')

    return _wrapper
