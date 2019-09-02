import logging
import traceback
import re
import os
from qtpy.QtCore import Property
from pydm.utilities import is_qt_designer, macro
from typing import Any, Callable, Optional
from .file_tracking import FileTracking


logger = logging.getLogger(__name__)


class ValueTransformationBase(FileTracking):
    """ Caveats:
        If you are using macros template in the imported modules, it will produce SyntaxError. Wrap it in strings.
    """

    def __init__(self):
        super().__init__()
        self._value_transform = ''
        self._value_transform_fn: Callable = None
        self._value_transform_macros = None
        self._value_transform_filename = None

    def getValueTransformation(self):
        """
        Python code snippet to transform the incoming value(s) before displaying it.

        Returns:
            Code snippet
        """
        return self._value_transform

    def setValueTransformation(self, new_formatter: str):
        """
        Reset generator code snippet.

        Args:
            new_val: New Python code snippet.
        """
        self._value_transform = str(new_formatter)

    valueTransformation = Property(str, getValueTransformation, setValueTransformation)

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

    def cached_value_transformation(self) -> Optional[Callable]:
        """
        When called for the first time, it will attempt to access inline code snippet
        or if one is undefined, then it will try to load a Python file, defined by the
        snippetFilename.

        Returns:
            Value transformation code with substituted macros.
        """
        if not self._value_transform_fn:
            if self.valueTransformation:
                parsed_code = self.substituted_string(self.valueTransformation)
                file = None
            else:
                file = self.relative_path(self.snippetFilename)
                parsed_code = self.open_file(file)
                file = os.path.abspath(file)
            if parsed_code:
                self._value_transform_fn = create_transformation_function(parsed_code, file=file)
        return self._value_transform_fn


class ValueTransformer(ValueTransformationBase):

    def getValueTransformation(self) -> str:
        return ValueTransformationBase.getValueTransformation(self)

    def setValueTransformation(self, new_formatter: str):
        """
        Reset generator code snippet.

        Args:
            new_val: New Python code snippet.
        """
        if self.getValueTransformation() != str(new_formatter):
            ValueTransformationBase.setValueTransformation(self, str(new_formatter))
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
            transform = self.cached_value_transformation()
            val = transform(new_val=new_val, widget=self) if transform else new_val
        super().value_changed(val)


def create_transformation_function(transformation: str, file: str = None) -> Callable:
    """
    Creates a function used to transform incoming value(s) into a single output value.

    Args:
        transformation: Python snippet.
        file: Path to the Python executable file to be set in __file__ variable.

    Returns:
        Function that can transform incoming values (passed as keyword args and are embedded into globals)
    """
    # For scripts that do not run code by default but rather expose functions,
    # pretend we are running them as the main target. However, if we simply change __name__ to '__main__',
    # imported packages will also see the same, which is not how it should be. Therefore we just
    # substitute all comparisons in the code against the '__main__' to True.
    code = re.sub(r'\_\_name\_\_\ *==\ *(\'(\'{2})?|\"(\"{2})?)\_\_main\_\_(\'(\'{2})?|\"(\"{2})?)', 'True', transformation)

    return_var = '__comrad_return_var__'

    # We wrap the code inside a dummy function so that user can use "return" statement in the code.
    wrapped_code = """
{return_var} = None

def {output_func_name}(val):
    global {return_var}
    {return_var} = val

__builtins__['output'] = {output_func_name}
{code}
""".format(output_func_name='__comrad_output_func__', return_var=return_var, code=code)
    global_base = globals().copy()
    if file:
        global_base['__file__'] = file
    del global_base['macro']
    del global_base['ValueTransformationBase']
    del global_base['FileTracking']
    del global_base['ValueTransformer']
    del global_base['create_transformation_function']

    def __comrad_dcode_wrapper__(**inputs) -> Any:
        global_vars = global_base.copy()  # Make sure to copy to not modify globals visible in the rest of the app
        global_vars.update(inputs)
        try:
            exec(wrapped_code, global_vars, {})
            try:
                return global_vars[return_var]  # This variable should have been set within wrapped_code
            except KeyError:
                return None
        except BaseException as e:
            last_stack_trace = traceback.format_exc().split('\n')[-3]
            logger.exception(f'ERROR: Exception occurred while running a transformation.\n'
                             f'{last_stack_trace}\n{e.__class__.__name__}: {str(e)}')

    return __comrad_dcode_wrapper__
