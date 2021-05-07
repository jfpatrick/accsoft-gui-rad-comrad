import os
import subprocess
import sys
import logging
import ast
from tempfile import TemporaryDirectory
from xml.etree.ElementTree import ElementTree, parse as parse_element_tree, ParseError
from ast import NodeVisitor, Import, ImportFrom
from dataclasses import dataclass
from pathlib import Path
from typing import Set, Callable, Optional, Iterable
from contextlib import contextmanager


logger = logging.getLogger(__name__)


@dataclass
class ScannedImport:
    pkg: str
    relative_loc: Optional[str]

    def __hash__(self):
        return hash(self.pkg) + 10000 * hash(self.relative_loc)

    @classmethod
    def create(cls, pkg: str, relative_loc: Optional[str]):
        return cls(pkg=pkg,
                   relative_loc=fs_path_to_pkg_path(relative_loc) if relative_loc is not None else None)


class ImportCollectorNodeVisitor(NodeVisitor):

    def __init__(self, relative_loc: Optional[str]):
        super().__init__()
        self.relative_loc = relative_loc
        self.imports: Set[ScannedImport] = set()

    def generic_visit(self, node):
        if isinstance(node, Import):
            for name in node.names:
                self.imports.add(ScannedImport.create(pkg=name.name, relative_loc=self.relative_loc))
        elif isinstance(node, ImportFrom):
            if node.level == 0 and node.module:  # only absolute imports
                self.imports.add(ScannedImport.create(pkg=node.module, relative_loc=self.relative_loc))
        NodeVisitor.generic_visit(self, node)


def get_relative_pkg_path(file: Path, basedir: Path) -> Optional[str]:
    relative_path = file.relative_to(basedir).parent
    relative_pkg: Optional[str] = str(relative_path).replace(os.sep, PKG_SEP)
    if relative_pkg == PKG_SEP:
        relative_pkg = None
    return relative_pkg


def get_imports_from_code(code: str, relative_loc: Optional[str]) -> Set[ScannedImport]:
    tree = ast.parse(code)
    node_visitor = ImportCollectorNodeVisitor(relative_loc)
    node_visitor.visit(tree)
    return node_visitor.imports


def scan_py_imports(py_file: Path, relative_loc: Optional[str]) -> Set[ScannedImport]:
    code = py_file.read_text()
    return get_imports_from_code(code, relative_loc)


def scan_ui_imports(ui_file: Path, relative_loc: Optional[str]) -> Set[ScannedImport]:
    try:
        tree = parse_element_tree(str(ui_file))
    except ParseError as e:
        logger.warning(f'{ui_file!s} cannot be parsed as XML: {e!s}')
        return set()

    # TODO: Need to scan python rules in the future
    return (scan_ui_custom_widgets(tree=tree, relative_loc=relative_loc)
            | scan_ui_inline_transformations(tree=tree, relative_loc=relative_loc, ui_file=ui_file)
            | scan_ui_referenced_python_files(tree=tree, relative_loc=relative_loc, ui_file=ui_file))


def scan_ui_custom_widgets(tree: ElementTree, relative_loc: Optional[str]) -> Set[ScannedImport]:
    imports: Set[ScannedImport] = set()
    for header in tree.findall('./customwidgets/customwidget/header'):
        if not header.text:
            continue
        # Strip file extension (if it is a file extension), but be careful, because it can also
        # represent a package path, e.g. "accwidgets.qt" is a valid package, and ".qt" here is not a
        # file extension, but a subpackage.
        # If the path is a file path, e.g. path/to/header.h, change it to path.to.header, just like PyQt does
        if header.text.endswith('.h'):
            header.text = header.text[:-2]
        elif header.text.endswith('.py'):
            header.text = header.text[:-3]
        header.text = fs_path_to_pkg_path(header.text)
        imports.add(ScannedImport.create(pkg=header.text, relative_loc=relative_loc))
    return imports


def scan_ui_inline_transformations(tree: ElementTree, ui_file: Path, relative_loc: Optional[str]) -> Set[ScannedImport]:
    imports: Set[ScannedImport] = set()
    for vt in tree.findall('.//property[@name="valueTransformation"]/string'):
        if vt.text:
            try:
                found_imports = get_imports_from_code(vt.text, relative_loc)
            except SyntaxError as e:
                logger.warning(f'valueTransformation "{vt.text}" inside {ui_file!s} contains invalid Python syntax: {e!s}')
            else:
                imports.update(found_imports)
    return imports


def scan_ui_referenced_python_files(tree: ElementTree, ui_file: Path, relative_loc: Optional[str]) -> Set[ScannedImport]:
    imports: Set[ScannedImport] = set()
    for sf in tree.findall('.//property[@name="snippetFilename"]/string'):
        if not sf.text:
            continue
        filename = ui_file.parent / sf.text
        if not filename.exists() or not filename.is_file():
            logger.warning(f"Indicated file {sf.text} inside {ui_file!s}'s snippetFilename cannot be opened")
            continue

        child_relative_pkg = get_relative_pkg_path(filename, ui_file.parent)
        if child_relative_pkg and relative_loc:
            temp_relative_loc: Optional[str] = PKG_SEP.join([relative_loc, child_relative_pkg])
        elif child_relative_pkg:
            temp_relative_loc = child_relative_pkg
        else:
            temp_relative_loc = relative_loc or None
        try:
            imports.update(scan_py_imports(filename, temp_relative_loc))
        except SyntaxError as e:
            logger.warning(f"Indicated file {sf.text} inside {ui_file!s}'s snippetFilename contains invalid Python "
                           f'syntax: {e!s}')
    return imports


def normalize_imports(used_imports: Set[ScannedImport], local_modules: Set[str]) -> Set[str]:
    # remove local "absolute" imports
    # i.e. `import reused` `from external import something`
    # where `ls $cwd` -> `app.ui reused.py external.py`
    known_external_imports: Set[str] = set()
    for file_import in used_imports:
        if not file_import.relative_loc:
            potential_local_import = file_import.pkg
        else:
            potential_local_import = PKG_SEP.join((file_import.relative_loc, file_import.pkg))
        for local in local_modules:
            if local.startswith(potential_local_import) and (len(local) == len(potential_local_import)
                                                             or local[len(potential_local_import)] == PKG_SEP):
                parent_dir = f'"{file_import.relative_loc}"' if file_import.relative_loc else 'root'
                logger.debug(f'"{file_import.pkg}" appears to be a local import, '
                             f'when used inside {parent_dir}')
                break
        else:
            known_external_imports.add(file_import.pkg)

    logger.debug(f'Known external imports: {known_external_imports}')

    top_level_modules = {imp.split(PKG_SEP)[0] for imp in known_external_imports}
    # Or also to get a static list, unreliable because of python version
    # https://docs.python.org/3/library/
    # modules = document.querySelectorAll('.py-mod')
    # module_names = [...modules].map(m => m.innerText)
    # module_names_base = module_names.map((m) => m.split(PKG_SEP)[0])
    # module_names_set = new Set(module_names_base)
    # console.log(JSON.stringify([...module_names_set]))

    # Before, module resolution was done using a fresh virtual environment, which had couple of problems:
    # 1 - It would include bundled acc-py modules, which are actually not from std lib, e.g. numpy
    # 2 - It was crashing pydev debugger in PyCharm
    # It now is encoded as a last resort fallback in find_std_lib_modules, but in reality must never be reached
    built_ins = set(find_std_lib_modules())
    if os.environ.get('ACC_PYTHON_ACTIVE', False):
        # Avoid over-locking to PyQt, let "comrad" steer PyQt by its dependencies
        built_ins.update({'PyQt5', 'PyQt6'})
    logger.debug(f"Built-ins that won't be considered: {built_ins}")
    not_built_ins = top_level_modules - built_ins

    return not_built_ins


@contextmanager
def execute_python(create_venv: bool = True):
    if create_venv:
        with TemporaryDirectory(prefix='comrad_package_imports_') as temp_dir:
            subprocess.check_call([sys.executable, '-m', 'venv', '--system-site-packages', temp_dir])
            yield str(Path(temp_dir) / 'bin' / 'python')
    else:
        yield sys.executable


def scan_imports(directory: Path) -> Set[str]:
    used_imports: Set[ScannedImport] = set()

    def scan(file_ext: str, scanner: Callable[[Path, Optional[str]], Set[ScannedImport]]) -> Set[Path]:
        files = set(directory.glob(f'**/*{os.extsep}{file_ext}'))
        for f in files:
            relative_pkg = get_relative_pkg_path(f, directory)
            file_imports = scanner(f, relative_pkg)
            found_imports = {e.pkg for e in file_imports}
            logger.debug(f'{f!s}: {found_imports or "--"}')
            used_imports.update(file_imports)
        return files

    def safe_scan_py_imports(py_file: Path, relative_loc: Optional[str]) -> Set[ScannedImport]:
        try:
            return scan_py_imports(py_file=py_file, relative_loc=relative_loc)
        except SyntaxError as e:
            logger.warning(f'{py_file!s} contains invalid Python syntax: {e!s}')
            return set()

    py_files = scan(file_ext='py', scanner=safe_scan_py_imports)
    scan(file_ext='ui', scanner=scan_ui_imports)

    # convert all the "relative" Python files to an import-like name "my/file.py" -> "my.file"
    local_modules = {fs_path_to_pkg_path(str(f.relative_to(directory).with_suffix('')))
                     for f in py_files}
    logger.debug(f'Local modules: {local_modules}')
    return normalize_imports(used_imports, local_modules)


def fs_path_to_pkg_path(input: str) -> str:
    return input.replace(os.sep, PKG_SEP)


def find_std_lib_modules() -> Iterable[str]:
    try:
        return sys.stdlib_module_names  # type: ignore  # Python 3.10 API
    except AttributeError:
        from stdlib_list import stdlib_list
        try:
            full_list = stdlib_list(f'{sys.version_info.major}.{sys.version_info.minor}')
        except ValueError:
            # Python version not found. In reality, must never happen, because the package bundles up until 3.9
            # And starting from 3.10, this block should not be executed.
            with execute_python() as py_executable:
                # Note that this crashes pydev debugger in PyCharm
                iter_modules_str = subprocess.check_output([py_executable, '-Ic',
                                                            'import pkgutil;print([m.name for m in pkgutil.iter_modules()])'])
                builtin_module_names_str = subprocess.check_output([py_executable, '-Ic',
                                                                    'import sys;print(list(sys.builtin_module_names))'])
                return set(eval(iter_modules_str) + eval(builtin_module_names_str))
        else:
            return {pkg.split(PKG_SEP)[0] for pkg in full_list}


PKG_SEP = '.'
