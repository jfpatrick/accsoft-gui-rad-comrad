import logging
import traceback
from qtpy.QtCore import Property
from typing import Any


logger = logging.getLogger(__name__)


class ValueTransformer:

    def __init__(self):
        self._value_transform = ''

    @Property(str)
    def valueTransformation(self):
        return self._value_transform

    @valueTransformation.setter
    def valueTransformation(self, new_formatter):
        if self._value_transform != str(new_formatter):
            self._value_transform = str(new_formatter)
            self.value_changed(self.value)


    def value_changed(self, new_val: Any) -> None:
        """
        Callback transforms the Channel value through the valueTransformation code before displaying it in a
        standard way.

        Args:
            new_val: The new value from the channel. The type depends on the channel.
        """
        val = _transform_value(new_val, transformation=self._value_transform) if self._value_transform else new_val
        super().value_changed(val)


def _transform_value(new_val: Any, transformation: str) -> Any:
    try:
        # We set to the same reference, for subclasses, that will rely on the same reference
        def returning_exec(code, globals=globals(), locals=locals()):
            indented_code = code.replace('\n', '\n    ')
            wrapped_code = f"""
global _return_val
def my_func():
    {indented_code}

_return_val = my_func()
"""
            exec(wrapped_code, globals, locals)
            return globals['_return_val']  # This variable should have been set within wrapped_code

        new_val = returning_exec(transformation, {'new_val': new_val})
    except BaseException as e:
        last_stack_trace = traceback.format_exc().split('\n')[-3]
        logger.exception(f'ERROR: Exception occurred while running a transformation.\n'
                         f'{last_stack_trace}\n{e.__class__.__name__}: {str(e)}')
    return new_val