"""
Module containing functionality to handle deprecated API.
"""

import functools
import logging
from typing import Dict, Any, Callable, cast, Optional
from types import MethodType


logger = logging.getLogger(__name__)


def deprecated_parent_prop(logger: logging.Logger, property_name: Optional[str] = None):
    """
    Decorator to deprecate properties exposed to Qt Designer that are actually defined in dependencies outside of ComRAD.

    Args:
        logger: Logger that should produce a warning (to localize where those warnings come from).
        property_name: If decorator is used on the property setter, it is better to give property name, rather than
                       the setter name, as they might be different.

    Returns:
        Wrapper method with decorated logic.
    """

    def _method_wrapper(method: MethodType):
        from comrad.widgets.mixins import CInitializedMixin
        from qtpy.QtWidgets import QWidget

        def _wrapper(self: CInitializedMixin, *_, **__):
            from pydm.utilities import is_qt_designer
            if not is_qt_designer():
                if not isinstance(self, CInitializedMixin) or not isinstance(self, QWidget):
                    raise TypeError(f'This decorator is intended to be used with CInitializedMixin on QWidget subclasses. {type(self).__name__} is not recognized as one.')
                if not self._widget_initialized:
                    # Ignore setting properties in __init__, which may come from PyDM superclasses
                    return
                name = cast(QWidget, self).objectName()
                if not name:
                    name = f'unidentified {type(self).__name__}'
                meth_name = property_name or method.__name__
                logger.warning(f'{meth_name} property is disabled in ComRAD (found in {name})')

        return _wrapper
    return _method_wrapper


def deprecated_args(**aliases: str) -> Callable:
    """
    Deprecation alias allows defining aliases for deprecated function
    parameters.

    Args:
        aliases: Mapping of deprecated parameter to the new parameter name
                 in the form old_name='new_name'
    """
    def _rename_kwargs(func_name: str,
                       kwargs: Dict[str, Any],
                       aliases: Dict[str, Any]) -> None:
        """
        Rename received keyword arguments.

        Args:
            func_name: Name of the function which's arguments are wrapped
            kwargs: Keyword Arguments passed to the function which was wrapped
            aliases: Aliases mapping the old kwarg names to the new ones
        """
        for alias, new in aliases.items():
            if alias in kwargs:
                if new in kwargs:
                    raise TypeError(f'"{func_name}" received both "{alias}" and "{new}"')
                logger.warning(f'Keyword-argument "{alias}" in function "{func_name}" is deprecated, use "{new}".')
                kwargs[new] = kwargs.pop(alias)

    def deco(f: Callable):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            _rename_kwargs(f.__name__, kwargs, aliases)
            return f(*args, **kwargs)
        return wrapper
    return deco
