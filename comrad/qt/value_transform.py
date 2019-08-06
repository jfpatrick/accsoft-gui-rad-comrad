import logging
import traceback
from qtpy.QtCore import Property
from pydm.utilities import is_qt_designer
from typing import Any, Dict


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
        if is_qt_designer():
            val = new_val  # Avoid code evaluation in Designer, as it can produce unnecessary errors with broken code
        else:
            val = (_transform_value(new_val, transformation=self._value_transform)
                   if self._value_transform else new_val)
        super().value_changed(val)


def _transform_value(new_val: Any, transformation: str) -> Any:
    global_scope = globals()
    global_scope['new_val'] = new_val
    return run_transformation(transformation, globals=global_scope)


def run_transformation(transformation: str, globals: Dict[str, Any] = globals(), locals: Dict[str, Any] = locals()) -> Any:
    """
    Run arbitrary Python code snippet to transform any incoming data into a single value.

    Incoming data can be defined using globals or locals and may depend on the use-case.

    Args:
        transformation: Python code snippet. It can have side-effects on the variables placed in globals and locals.
        globals: Global variables in the scope visible to the transformation code
        locals: Local variables in the scope visible to the transformation code

    Returns:
        A single resulting value.
    """
    try:
        # We set to the same reference, for subclasses, that will rely on the same reference
        def returning_exec(code, globals=globals, locals=locals):
            indented_code = code.replace('\n', '\n    ')
            wrapped_code = f"""
global _return_val
def my_func():
    {indented_code}

_return_val = my_func()
"""
            exec(wrapped_code, globals, locals)
            return globals['_return_val']  # This variable should have been set within wrapped_code

        return returning_exec(transformation, globals=globals, locals=locals)
    except BaseException as e:
        last_stack_trace = traceback.format_exc().split('\n')[-3]
        logger.exception(f'ERROR: Exception occurred while running a transformation.\n'
                         f'{last_stack_trace}\n{e.__class__.__name__}: {str(e)}')