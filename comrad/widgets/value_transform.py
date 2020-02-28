import logging
import re
import copy
from pathlib import Path
from string import Template
from typing import Callable, Optional, Any, cast
from qtpy.QtCore import Property
from pydm.utilities import macro, find_file
from pydm.widgets.base import PyDMPrimitiveWidget


logger = logging.getLogger(__name__)


class CFileTracking:

    def open_file(self, full_path: Optional[Path]) -> str:
        """
        Opens the file and parses macros inside.

        Args:
            full_path: Absolute path to the Python snippet.

        Returns:
            Parsed contents of the file with substituted macros.
        """
        if not full_path:
            return ''
        return macro.substitute_in_file(file_path=str(full_path), macros=self.parsed_macros()).getvalue()

    def parsed_macros(self):
        """
        Dictionary containing the key value pair for each macro specified.

        Returns
        --------
            Dictionary
        """
        parent_display = cast(PyDMPrimitiveWidget, self).find_parent_display()
        parent_macros = {}
        if parent_display:
            parent_macros = copy.copy(parent_display.macros())
        widget_macros = macro.parse_macro_string(self.macros)
        parent_macros.update(widget_macros)
        return parent_macros

    def substituted_string(self, string: str) -> str:
        """
        Similar to :func:`pydm.utilities.macro.substitute_in_file` this method substitutes macros in a string
        directly, without opening a file.

        Args:
            string: String to parse.
            macros: Macros dictionary.

        Returns:
            String with substituted macros.
        """
        text = Template(string)
        return macro.replace_macros_in_template(template=text, macros=self.parsed_macros()).getvalue()


class CValueTransformationBase(CFileTracking):
    """ Caveats:
        If you are using macros template in the imported modules, it will produce :class:`SyntaxError`.
        Wrap it in strings.
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

    def _get_snippet_filename(self) -> str:
        return self._value_transform_filename

    def _set_snippet_filename(self, new_val: str):
        self._value_transform_filename = new_val

    snippetFilename = Property(str, _get_snippet_filename, _set_snippet_filename)
    """
    Path to the file that contains Python snippet for transformation.
    If :attr:`~comrad.widgets.value_transform.CValueTransformationBase.valueTransformation` is defined,
    it will override the code coming from this file.
    """

    def _get_macros(self) -> str:
        if self._value_transform_macros is None:
            return ''
        return self._value_transform_macros

    def _set_macros(self, new_macros: str):
        self._value_transform_macros = str(new_macros)

    macros = Property(str, _get_macros, _set_macros)
    """
    Similar to the macros of :class:`pydm.widgets.PyDMEmbeddedDisplay` and
    :class:`pydm.widgets.PyDMRelatedDisplayButton`,
    this is will substitute variables in the value transformation code,
    either defined with the inline snippet, or coming from a file.
    String must be JSON-formatted.
    """

    def parsed_macros(self):
        m = super().parsed_macros()
        m.update(macro.parse_macro_string(self.macros))
        return m

    def cached_value_transformation(self) -> Optional[Callable]:
        """
        When called for the first time, it will attempt to access inline code snippet
        or if one is undefined, then it will try to load a Python file, defined by the
        :attr:`snippetFilename`.

        Returns:
            Value transformation code with substituted macros.
        """
        if not self._value_transform_fn:
            if not self.valueTransformation and not self.snippetFilename:
                parsed_code = None
            else:
                parent_display = cast(PyDMPrimitiveWidget, self).find_parent_display()
                parent_display_file: Optional[Path] = None
                if parent_display:
                    parent_display_file = Path(parent_display.loaded_file()).absolute()

                if self.valueTransformation:
                    parsed_code = self.substituted_string(self.valueTransformation)
                    file = parent_display_file
                elif self.snippetFilename:
                    base_path: Optional[Path] = None
                    if parent_display_file:
                        base_path = parent_display_file.parent
                    file_path = find_file(fname=self.snippetFilename, base_path=base_path)
                    if file_path:
                        file = Path(file_path).absolute()
                        parsed_code = self.open_file(file)
                    else:
                        parsed_code = None

            if parsed_code:
                self._value_transform_fn = _create_transformation_function(parsed_code, file=file)
        return self._value_transform_fn


def _create_transformation_function(transformation: str, file: Optional[Path] = None) -> Callable:
    """
    Creates a function used to transform incoming value(s) into a single output value.

    Args:
        transformation: Python snippet.
        file: Path to the Python executable file to be set in ``__file__`` variable. This will also set sys.path to
            its containing directory, so that imports of the adjacent files are possible.

    Returns:
        Function that can transform incoming values (passed as keyword args and are embedded into globals)
    """
    # For scripts that do not run code by default but rather expose functions,
    # pretend we are running them as the main target. However, if we simply change __name__ to '__main__',
    # imported packages will also see the same, which is not how it should be. Therefore we just
    # substitute all comparisons in the code against the '__main__' to True.
    code = re.sub(pattern=r'\_\_name\_\_\ *==\ *(\'(\'{2})?|\"(\"{2})?)\_\_main\_\_(\'(\'{2})?|\"(\"{2})?)',
                  repl='True',
                  string=transformation)

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
        global_base['__file__'] = str(file)
    del global_base['macro']
    del global_base[find_file.__name__]
    del global_base[CValueTransformationBase.__name__]
    del global_base[CFileTracking.__name__]
    del global_base[_create_transformation_function.__name__]
    del global_base[PyDMPrimitiveWidget.__name__]

    if file:
        # Make sure "import local_file" is possible from the included script
        # This will use the containing directory of the Python file for the widgets using snippetFilename
        # or containing directory for the *.ui file for widgets using valueTransformation.
        import sys
        sys.path.insert(0, str(file.parent))

    def __comrad_dcode_wrapper__(**inputs) -> Any:
        import traceback
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
