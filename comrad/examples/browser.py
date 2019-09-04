"""
ComRAD Examples browser is a tool to browse through sources and run interactive examples
how to use ComRAD ecosystem.
"""

import os
import logging
import types
import argparse
import importlib
import importlib.util
import importlib.machinery
from typing import List, Optional, Tuple, cast, Union
from qtpy import uic
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor, QShowEvent
from qtpy.QtWidgets import (QMainWindow, QTreeWidgetItem, QTreeWidget, QStackedWidget, QTabWidget, QApplication,
                            QAbstractScrollArea, QLabel, QPushButton, QVBoxLayout, QWidget, QTextEdit)
from comrad import __version__, __author__
from comrad.utils import icon

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
    _QSCI_AVAILABLE = True
except ImportError:
    _QSCI_AVAILABLE = False


logging.basicConfig()  # Because can be run as a standalone module
logger = logging.getLogger(__name__)


_EXAMPLE_CONFIG = '__init__.py'
_EXAMPLE_DETAILS_INTRO_PAGE = 0
_EXAMPLE_DETAILS_DETAILS_PAGE = 1

_EXAMPLE_DETAILS_UI_PAGE = 1
_EXAMPLE_DETAILS_PY_PAGE = 0


_CURR_DIR = os.path.dirname(__file__)

PathLike = Union[os.PathLike, str]


class ExamplesWindow(QMainWindow):
    """Main window of the examples launcher."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # For IDE support, assign types to dynamically created items from the *.ui file
        self.example_details: QStackedWidget = None
        self.examples_tree: QTreeWidget = None
        self.example_desc_label: QLabel = None
        self.example_title_label: QLabel = None
        self.example_run_btn: QPushButton = None
        self.tabs: QTabWidget = None

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'main.ui'), self)

        self._selected_example_path: Optional[str] = None
        self._selected_example_entrypoint: Optional[str] = None
        self._selected_example_japc_generator: Optional[str] = None

        self.example_details.setCurrentIndex(_EXAMPLE_DETAILS_INTRO_PAGE)

        self.actionAbout.triggered.connect(self._show_about)
        self.actionExit.triggered.connect(self.close)

        examples = ExamplesWindow._find_runnable_examples()

        def replace_digits(orig: str) -> str:
            """
            Sorts the strings preferring 1.10 to fall after 1.1 which is not achieved by
            default ASCII sorting which prefers 0 as the lower char code.
            Args:
                sample1: string to compare.

            Returns:
                replaced string

            """
            import re

            # Replaces a digit by the corresponding amount of letters that are low in the ASCII table
            replace_num = lambda match: int(match.group(0)) * 'Z'
            return re.sub(pattern=r'\d+',
                          repl=replace_num,
                          string=orig)

        examples.sort(key=replace_digits, reverse=True)
        self._populate_examples_tree_widget(examples)

        self.examples_tree.itemActivated.connect(self._on_example_selected)
        self.examples_tree.itemClicked.connect(self._on_example_selected)
        self.example_run_btn.clicked.connect(self._run_example)
        self.show()

    def _show_about(self):  # pylint: disable=no-self-use   # It has to be instance method, as it is connected as a slot
        """
        Opens 'About' dialog.

        The information shown in the dialog is parsed from the 'comrad' package.
        In addition, email of the author is parsed to create a clickable link for support.
        """
        dialog = uic.loadUi(os.path.join(os.path.dirname(__file__), 'about.ui'))
        dialog.version_label.setText(str(__version__))

        # Parse email to create a link
        import re
        match = re.match(pattern='([^<]*)(<([^>]*)>)', string=__author__)
        support = match.group(1).strip()
        if len(match.groups()) > 2:
            email = match.group(3)
            support += f' &lt;<a href="mailto:{email}">{email}</a>&gt;'

        dialog.support_label.setText(support)
        dialog.exec_()

    @staticmethod
    def _find_runnable_examples() -> List[str]:
        """
        Crawls the examples folder trying to locate subdirectories that can be runnable examples.

        A runnable example is any subdirectory that has __init__.py file inside.
        The crawling is done recursively, but subdirectories of runnable examples are not crawled
        because they might contain code that is not supposed to be top-level examples.

        Returns:
            list of absolute paths to runnable examples.
        """
        excludes = {'_', '.'}
        example_paths: List[str] = []
        for root, dirs, files in os.walk(_CURR_DIR):
            logger.debug(f'Entering {root}')
            is_exec = _EXAMPLE_CONFIG in files
            if root != _CURR_DIR and is_exec:
                example_paths.append(root)
                logger.debug(f'Example {root} is executable. Will stop here.')
                dirs[:] = []  # Do not go deeper, as it might simply contain submodules
            else:
                dirs[:] = [d for d in dirs if d[0] not in excludes]
                logger.debug(f'Will crawl child dirs: {dirs}')

        formatted = '\n'.join(example_paths)
        logger.debug(f'Located examples in dirs:\n{formatted}')
        return example_paths

    def _populate_examples_tree_widget(self, example_paths: List[str]):
        """
        Populates sidebar with the runnable examples.

        The tree will reflect directory structure, meaning that examples can be scoped
        under directories that are not runnable examples themselves.

        Args:
            example_paths: list of absolute paths to the runnable examples.
        """
        for path in example_paths:
            relative = os.path.relpath(path, _CURR_DIR)
            dirs = relative.split(os.path.sep)
            parent_subtree: QTreeWidgetItem = self.examples_tree.invisibleRootItem()
            for directory in dirs:
                name, dig = ExamplesWindow._tree_info(directory)
                curr_subtree: Optional[QTreeWidgetItem] = None
                for idx in range(parent_subtree.childCount()):
                    child = parent_subtree.child(idx)
                    if child.text(1) == directory:
                        curr_subtree = child
                        break
                if not curr_subtree:
                    par_dig = parent_subtree.data(2, Qt.DisplayRole)
                    if par_dig:
                        dig = f'{par_dig}.{dig}'
                    if dig:
                        name = f'{dig}. {name}'
                    curr_subtree = QTreeWidgetItem(parent_subtree, [name, directory, dig])
                parent_subtree = curr_subtree

    @staticmethod
    def _tree_info(name: str) -> Tuple[str, Optional[str]]:
        """
        Converts the snake-cased directory name of an example into a human-readable
        format. It also adds a complementary ordinal number to assist content numbering.

        Args:
            name: original name.

        Returns:
            beautified name.
        """
        components = name.split('_')
        dig: Optional[str]
        try:
            dig = components[0]
        except IndexError:
            return name, None
        if dig.isdigit():
            components.remove(components[0])
        else:
            dig = None

        return ' '.join(components).title(), dig

    def _on_example_selected(self, item: QTreeWidgetItem):
        """
        Slot for the sidebar example tree item to get selected by the user.

        Args:
            item: tree item that has been selected.
        """
        name = item.data(1, Qt.DisplayRole)  # Fetch the second column, which is the original dir name
        # Allow selecting only leaf items
        if item.childCount() > 0:
            logger.debug(f'Ignoring selection of {name} - not a leaf element')
            return
        curr_item = item
        path_dirs = []
        while True:
            par = curr_item.parent()
            path_dirs.append(curr_item.data(1, Qt.DisplayRole))  # Fetch the second column, which is the original dir name
            if not par:
                break
            curr_item = par

        path_dirs.reverse()
        example_path = os.path.join(os.path.dirname(__file__), *path_dirs)

        if self._selected_example_path == example_path:
            # Already selected. Do nothing
            return

        self._selected_example_path = example_path
        example_mod = ExamplesWindow._module_from_example(basedir=example_path, name=name)
        if example_mod:
            self._set_example_details(module=example_mod, basedir=example_path)

    def _set_example_details(self, module: types.ModuleType, basedir: PathLike):
        """
        Populates the details view (right-hand side of the window) with information about the
        selected example.

        It parses the configuration file of the module that should have been located before.

        Args:
            module: loaded Python module that represents the package with example contents.
            basedir: absolute path to the example.
        """
        example_fgen: Optional[str]
        try:
            example_entrypoint: str = module.entrypoint  # type: ignore
            example_title: str = module.title  # type: ignore
            example_description: str = module.description  # type: ignore
        except AttributeError as ex:
            logger.warning(f'Cannot display example - config file is incomplete: {str(ex)}')
            return
        try:
            example_fgen = module.japc_generator  # type: ignore
        except AttributeError:
            example_fgen = None

        self._selected_example_japc_generator = (
            f'{ExamplesWindow._absolute_module_id(basedir=basedir)}.{example_fgen}'
            if example_fgen else None
        )
        self._selected_example_entrypoint = example_entrypoint
        self.example_title_label.setText(example_title)
        self.example_desc_label.setText(example_description)

        self.example_details.setCurrentIndex(_EXAMPLE_DETAILS_DETAILS_PAGE)

        bundle_files: List[str] = []

        def is_file_allowed(file: PathLike) -> bool:
            _, ext = os.path.splitext(file)
            return ext in ('.py', '.ui', '.json')

        for root, dirs, files in os.walk(basedir):
            try:
                dirs.remove('__pycache__')
            except ValueError:
                pass
            if root == basedir:
                files.remove(_EXAMPLE_CONFIG)
            files = cast(List[str], filter(is_file_allowed, files))
            bundle_files.extend(os.path.join(root, f) for f in files)

        self._create_file_tabs(file_paths=bundle_files, selected=example_entrypoint, basedir=basedir)

    def _create_file_tabs(self, file_paths: List[str], selected: str, basedir: PathLike):
        """
        Dynamically creates tabs to select files contained by the example directory.

        Args:
            file_paths: paths of the files to create tabs for.
            selected: name of the selected file by default.
            basedir: absolute path to the module.
        """
        for _ in range(self.tabs.count()):
            self.tabs.removeTab(0)

        for file_path in file_paths:
            widget: QWidget
            filename = os.path.relpath(path=file_path, start=basedir)
            _, ext = os.path.splitext(filename)
            if ext in ('.py', '.json'):
                widget = EditorTab(file_path, self.tabs)
            elif ext == '.ui':
                tab = DesignerTab(file_path, self.tabs)
                tab.designer_opened.connect(ExamplesWindow._open_designer_file)
                widget = tab
            self.tabs.addTab(widget, filename)
            if filename == selected:
                # Trigger display of the main file
                self.tabs.setCurrentWidget(widget)

    @staticmethod
    def _absolute_module_id(basedir: PathLike) -> str:
        """
        Constructs the absolute module identifier.

        Because we are importing via importlib, the resulting identifier will be relative and will not
        include paths to the examples module itself.

        Args:
            basedir: absolute path to the module

        Returns:
            absolute identifier.
        """
        # Removes trailing '.__main__'
        abs_mod_path: List[str] = __loader__.name.split('.')  # type: ignore
        del abs_mod_path[-1]
        rel_path = os.path.relpath(basedir, _CURR_DIR)
        abs_mod_path.extend(rel_path.split(os.sep))
        return '.'.join(abs_mod_path)

    @staticmethod
    def _module_from_example(basedir: PathLike, name: str) -> Optional[types.ModuleType]:
        """
        Resolves the Python module from the directory of the example.

        Args:
            basedir: absolute path to the example.
            name: name of the example to be set for the module.

        Returns:
            Python module or None if failed to load.
        """
        if not os.path.isdir(basedir):
            logger.warning(f'Cannot display example from {basedir} - not a directory')
            return None

        config = os.path.join(basedir, _EXAMPLE_CONFIG)
        if not os.path.exists(config) or not os.path.isfile(config):
            logger.warning(f'Cannot display example from {basedir} - cannot find entry point')
            return None

        spec: importlib.machinery.ModuleSpec = importlib.util.spec_from_file_location(name=name, location=config)
        mod: types.ModuleType = importlib.util.module_from_spec(spec)
        loader = cast(importlib.machinery.SourceFileLoader, spec.loader)
        try:
            loader.exec_module(mod)
        except ImportError as ex:
            logger.warning(f'Cannot import example from {basedir}: {str(ex)}')
            return None
        return mod

    def _run_example(self):
        """Opens runtime application for the example."""
        if not self._selected_example_entrypoint or not self._selected_example_path:
            logger.warning(f"Won't run example. Entrypoint is undefined.")
            return None

        # We must run it as an external process, because event loop is already running
        file_path = os.path.join(self._selected_example_path, self._selected_example_entrypoint)
        args: List[str] = ['comrad', 'run', file_path]
        env = dict(os.environ, PYJAPC_SIMULATION_INIT=(self._selected_example_japc_generator or ''))
        python_path = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f'{_CURR_DIR}:{python_path}'

        import subprocess
        try:
            return subprocess.run(args=args, shell=False, env=env, check=True)
        except subprocess.CalledProcessError as ex:
            logger.error(f'comrad run has failed: {str(ex)}')

    @staticmethod
    def _open_designer_file(file_path: PathLike):
        """Opens *.ui file in Qt Designer"""
        from comrad.launcher.designer import run_designer
        run_designer(files=[cast(str, file_path)])


class DesignerTab(QWidget):
    """Page for the Qt Designer view in the example details."""

    designer_opened = Signal([str])

    def __init__(self, file_path: PathLike, parent: Optional[QWidget] = None, *args):
        super().__init__(parent, *args)
        self._file_path = file_path
        self.designer_btn: Optional[QPushButton] = None

    def _btn_clicked(self):
        """Forwards the signal adding path information"""
        self.designer_opened.emit(self._file_path)

    def showEvent(self, event: QShowEvent) -> None:
        """Creates code editor when shown for the first time."""
        super().showEvent(event)

        if self.designer_btn is not None:
            return

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'ui_details.ui'), self)
        btn: QPushButton = self.designer_btn  # Remove optional, as we are sure it was set here
        btn.clicked.connect(self._btn_clicked)


class EditorTab(QWidget):
    """Page for the text file editor in the example details."""

    def __init__(self, file_path: PathLike, parent: Optional[QWidget] = None, *args):
        super().__init__(parent, *args)
        self._file_path = file_path
        self.code_viewer: Optional[QAbstractScrollArea] = None

    def showEvent(self, event: QShowEvent) -> None:
        """Creates code editor when shown for the first time."""
        super().showEvent(event)

        # Not a first show event
        if self.code_viewer is not None:
            return

        if _QSCI_AVAILABLE:
            editor = QsciScintilla()
            # Python lexer should cover all our use-cases: Python code + JSON
            # (which looks like a subset of Python lists/dictionaries)
            lexer = QsciLexerPython(editor)
            editor.setLexer(lexer)
            editor.setIndentationsUseTabs(False)
            editor.setIndentationGuides(True)
            editor.setTabWidth(4)
            editor.setEolMode(QsciScintilla.EolUnix)
            editor.setCaretLineVisible(True)
            editor.setCaretLineBackgroundColor(QColor('#efefef'))
            editor.setMargins(1)
            editor.setMarginType(0, QsciScintilla.NumberMargin)
            editor.setMarginWidth(0, 40)
            editor.setUtf8(True)
            editor.setReadOnly(True)
            self.code_viewer = editor
        else:
            editor = QTextEdit()
            editor.setUndoRedoEnabled(False)
            editor.setReadOnly(True)
            editor.setAcceptRichText(False)
            self.code_viewer = editor

        with open(self._file_path) as f:
            self.code_viewer.setText(f.read())

        layout = QVBoxLayout()
        layout.addWidget(self.code_viewer)
        layout.setContentsMargins(0, 0, 0, 1)
        self.setLayout(layout)


def populate_parser(parser: argparse.ArgumentParser):
    """This is a reusable parser builder to facilitate main parser as well as subparsers

    Args:
        parser: parser to populate
    """
    parser.add_argument('--debug',
                        help='enable debug output of this example launcher',
                        dest='debug',
                        action='store_true')
    parser.set_defaults(debug=False)


def run_browser(args: argparse.Namespace):
    """Runs the examples browser with the given command-line arguments.

    Args:
        args: parsed command line arguments
    """
    import sys
    # Set explicitly because root one is NOTSET
    # When used from ComRAD main entry point
    logging.getLogger('').setLevel(logging.DEBUG if args.debug else logging.WARNING)
    app_args = ['ComRAD examples']
    app_args.extend(sys.argv)
    app = QApplication(app_args)
    import comrad.qt
    app.setWindowIcon(icon('app', module_path=comrad.qt.application))
    _ = ExamplesWindow()
    sys.exit(app.exec_())
