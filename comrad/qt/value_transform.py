import logging
import traceback
import re
from qtpy.QtCore import Property
from pydm.utilities import is_qt_designer, macro
from typing import Any, Dict
from .file_tracking import FileTracking


logger = logging.getLogger(__name__)


class ValueTransformationBase(FileTracking):

    def __init__(self):
        super().__init__()
        self._value_transform = ''
        self._value_transform_parsed = ''
        self._value_transform_macros = None
        self._value_transform_filename = None

    @Property(str)
    def valueTransformation(self):
        """
        Python code snippet to transform the incoming value(s) before displaying it.

        Returns:
            Code snippet
        """
        return self._value_transform

    @valueTransformation.setter
    def valueTransformation(self, new_formatter):
        """
        Reset generator code snippet.

        Args:
            new_val: New Python code snippet.
        """
        if self._value_transform != str(new_formatter):
            self._value_transform = str(new_formatter)
            self.value_changed(self.value)

    @Property(str)
    def snippetFilename(self) -> str:
        """
        Path to the file that contains Python snippet for transformation. If valueTransformation is defined,
        it will override the code coming from this file.

        Returns:
            Filename of the Python file.
        """
        return self._value_transform_filename

    @snippetFilename.setter
    def snippetFilename(self, new_val: str):
        """
        Sets the path to the Python file.

        Args:
            new_val: Filename of the Python code.
        """
        self._value_transform_filename = new_val

    @Property(str)
    def macros(self) -> str:
        """
        Similar to the macros of PyDMEmbeddedDisplay and PyDMRelatedDisplayButton,
        this is will substitute variables in the value transformation code,
        either defined with the inline snippet, or coming from a file.

        Returns:
            JSON-formatted string containing macro variables.
        """
        if self._value_transform_macros is None:
            return ''
        return self._value_transform_macros

    @macros.setter
    def macros(self, new_macros: str):
        """
            JSON-formatted string containing macro variables.

        Args:
            new_macros: new string.
        """
        self._value_transform_macros = str(new_macros)

    def parsed_macros(self):
        m = super().parsed_macros()
        m.update(macro.parse_macro_string(self.macros))
        return m

    def cached_value_transformation(self) -> str:
        """
        When called for the first time, it will attempt to access inline code snippet
        or if one is undefined, then it will try to load a Python file, defined by the
        snippetFilename.

        Returns:
            Value transformation code with substituted macros.
        """
        if not self._value_transform_parsed:
            if self.valueTransformation:
                self._value_transform_parsed = self.substituted_string(self.valueTransformation)
            else:
                self._value_transform_parsed = self.open_file(self.snippetFilename)
        return self._value_transform_parsed


class ValueTransformer(ValueTransformationBase):

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
            code = self.cached_value_transformation()
            val = _transform_value(new_val, transformation=code) if code else new_val
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
            code = re.sub(r'\_\_name\_\_\ *==\ *(\'(\'{2})?|\"(\"{2})?)\_\_main\_\_(\'(\'{2})?|\"(\"{2})?)', 'True', code)
            indented_code = code.replace('\n', '\n    ')
            # For scripts that do not run code by default but rather expose functions,
            # pretend we are running them as the main target. However, if we simply change __name__ to '__main__',
            # imported packages will also see the same, which is not how it should be. Therefore we just
            # substitute all comparisons in the code against the '__main__' to True.
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