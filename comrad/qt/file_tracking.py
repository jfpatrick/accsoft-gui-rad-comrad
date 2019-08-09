import os
from string import Template
from pydm.utilities import is_pydm_app, macro

class FileTracking:

    def __init__(self):
        self.base_path = ''
        self.base_macros = {}
        if is_pydm_app():
            self.base_path = self.app.directory_stack[-1]
            self.base_macros = self.app.macro_stack[-1]

    def open_file(self, filename: str) -> str:
        """
        Opens the file and parses macros inside.

        Args:
            filename: Filename of the Python snippet.

        Returns:
            Parsed contents of the file with substituted macros.
        """
        if not filename:
            return ''
        path = os.path.expanduser(os.path.expandvars(filename))
        file_path = os.path.join(self.base_path, path) if self.base_path else path
        return macro.substitute_in_file(file_path=file_path, macros=self.parsed_macros()).getvalue()

    def parsed_macros(self):
        """
        Dictionary containing the key value pair for each macro specified.

        Returns
        --------
        dict
        """
        return macro.find_base_macros(self)

    def substituted_string(self, string: str) -> str:
        """
        Similar to  macro.substitute_in_file() this method substitutes macros in a string
        directly, without opening a file.

        Args:
            string: String to parse.
            macros: Macros dictionary.

        Returns:
            String with substituted macros.
        """
        text = Template(string)
        return macro.replace_macros_in_template(template=text, macros=self.parsed_macros()).getvalue()