import logging
from types import MethodType
from typing import cast
from qtpy.QtWidgets import QWidget


def superclass_deprecated(logger: logging.Logger):
    """
    Decorator to deprecate properties exposed to Qt Designer that are actually defined in dependencies outside of ComRAD.

    Args:
        logger: Logger that should produce a warning (to localize where those warnings come from)

    Returns:
        Wrapper method with decorated logic.
    """

    def _method_wrapper(method: MethodType):
        from comrad.widgets.mixins import CInitializedMixin

        def _wrapper(self: CInitializedMixin, *_, **__):
            from pydm.utilities import is_qt_designer
            if not is_qt_designer():
                if not isinstance(self, CInitializedMixin):
                    raise TypeError(f'This decorator is intended to be used with CInitializedMixin. {type(self).__name__} is not recognized as one.')
                if not self._widget_initialized:
                    # Ignore setting properties in __init__, which may come from PyDM superclasses
                    return
                name = cast(QWidget, self).objectName()
                if not name:
                    name = f'unidentified {type(self).__name__}'
                logger.warning(f'{method.__name__} property is disabled in ComRAD (found in {name})')

        return _wrapper
    return _method_wrapper
