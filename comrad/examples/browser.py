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
from pathlib import Path
from typing import List, Optional, Tuple, cast, Union
from qtpy import uic
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QShowEvent
from qtpy.QtWidgets import (QMainWindow, QTreeWidgetItem, QTreeWidget, QStackedWidget, QTabWidget, QApplication,
                            QAbstractScrollArea, QLabel, QPushButton, QVBoxLayout, QWidget, QTextEdit, QFrame)
from pydm.utilities.iconfont import IconFont
from comrad.icons import icon
from comrad.app.about import AboutDialog

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciLexerJSON, QsciLexerCSS
    _QSCI_AVAILABLE = True
except ImportError:
    _QSCI_AVAILABLE = False


logger = logging.getLogger(__name__)


_EXAMPLE_CONFIG = '__init__.py'
_EXAMPLE_DETAILS_INTRO_PAGE = 0
_EXAMPLE_DETAILS_DETAILS_PAGE = 1

_EXAMPLE_DETAILS_UI_PAGE = 1
_EXAMPLE_DETAILS_PY_PAGE = 0


_CURR_DIR: Path = Path(__file__).parent.absolute()


class ExamplesWindow(QMainWindow):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 flags: Optional[Union[Qt.WindowFlags, Qt.WindowType]] = None):
        """
        Main window of the examples launcher.

        Args:
            parent: Parent widget to hold this object.
            flags: Configuration flags to be passed to Qt.
        """
        if flags is None:
            flags = Qt.WindowFlags()
        super().__init__(parent, flags)

        # For IDE support, assign types to dynamically created items from the *.ui file
        self.example_details: QStackedWidget = None
        self.examples_tree: QTreeWidget = None
        self.example_desc_label: QLabel = None
        self.example_title_label: QLabel = None
        self.example_run_btn: QPushButton = None
        self.arg_lbl: QLabel = None
        self.arg_frame: QFrame = None
        self.alert_icon_lbl: QLabel = None
        self.tabs: QTabWidget = None

        uic.loadUi(_CURR_DIR / 'main.ui', self)

        self._selected_example_path: Optional[Path] = None
        self._selected_example_entrypoint: Optional[str] = None
        self._selected_example_japc_generator: Optional[str] = None
        self._selected_example_args: Optional[List[str]] = None

        self.alert_icon_lbl.setPixmap(IconFont().icon('exclamation-triangle').pixmap(self.alert_icon_lbl.minimumSize()))
        self.arg_frame.hide()

        self.example_details.setCurrentIndex(_EXAMPLE_DETAILS_INTRO_PAGE)

        self.actionAbout.triggered.connect(self._show_about)
        self.actionExit.triggered.connect(self.close)

        examples = ExamplesWindow._find_runnable_examples()

        def replace_digits(orig: Path) -> Path:
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
            return Path(re.sub(pattern=r'\d+',
                               repl=replace_num,
                               string=str(orig)))

        examples.sort(key=replace_digits, reverse=True)
        self._populate_examples_tree_widget(examples)

        self.examples_tree.itemActivated.connect(self._on_example_selected)
        self.examples_tree.itemClicked.connect(self._on_example_selected)
        self.example_run_btn.clicked.connect(self._run_example)
        self.show()

    def _show_about(self):
        """
        Opens 'About' dialog.
        """
        AboutDialog(parent=self, icon=self.windowIcon()).show()

    @staticmethod
    def _find_runnable_examples() -> List[Path]:
        """
        Crawls the examples folder trying to locate subdirectories that can be runnable examples.

        A runnable example is any subdirectory that has __init__.py file inside.
        The crawling is done recursively, but subdirectories of runnable examples are not crawled
        because they might contain code that is not supposed to be top-level examples.

        Returns:
            list of absolute paths to runnable examples.
        """
        excludes = {'_', '.'}
        example_paths: List[Path] = []
        for root, dirs, files in os.walk(_CURR_DIR):
            root_path = Path(root)
            logger.debug(f'Entering {root_path}')
            is_exec = _EXAMPLE_CONFIG in files
            if root_path != _CURR_DIR and is_exec:
                example_paths.append(root_path)
                logger.debug(f'Example {root_path} is executable. Will stop here.')
                dirs[:] = []  # Do not go deeper, as it might simply contain submodules
            else:
                dirs[:] = [d for d in dirs if d[0] not in excludes]
                logger.debug(f'Will crawl child dirs: {dirs}')

        logger.debug('Located examples in dirs:\n{paths}'.format(paths='\n'.join(map(str, example_paths))))
        return example_paths

    def _populate_examples_tree_widget(self, example_paths: List[Path]):
        """
        Populates sidebar with the runnable examples.

        The tree will reflect directory structure, meaning that examples can be scoped
        under directories that are not runnable examples themselves.

        Args:
            example_paths: list of absolute paths to the runnable examples.
        """
        for path in example_paths:
            relative = path.relative_to(_CURR_DIR)
            dirs = relative.parts
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
        example_path = _CURR_DIR.joinpath(*path_dirs)

        if self._selected_example_path == example_path:
            # Already selected. Do nothing
            return

        self._selected_example_path = example_path
        example_mod = ExamplesWindow._module_from_example(basedir=example_path, name=name)
        if example_mod:
            self._set_example_details(module=example_mod, basedir=example_path)

    def _set_example_details(self, module: types.ModuleType, basedir: Path):
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

        example_args: Optional[List[str]]

        def expand_args(arg: str) -> str:
            import re
            return re.sub(pattern=r'^~example', repl=str(basedir), string=arg)

        try:
            example_args = list(map(expand_args, module.launch_arguments))  # type: ignore
        except AttributeError:
            example_args = None

        self._selected_example_japc_generator = (
            f'{ExamplesWindow._absolute_module_id(basedir=basedir)}.{example_fgen}'
            if example_fgen else None
        )
        self._selected_example_entrypoint = example_entrypoint
        self._selected_example_args = example_args
        self.example_title_label.setText(example_title)
        self.example_desc_label.setText(example_description)

        self.example_details.setCurrentIndex(_EXAMPLE_DETAILS_DETAILS_PAGE)

        if example_args:
            self.arg_frame.show()
            self.arg_lbl.setText('\n'.join(example_args))
        else:
            self.arg_frame.hide()

        bundle_files: List[Path] = []

        def is_file_allowed(file: str) -> bool:
            ext = Path(file).suffix
            return ext in ('.py', '.ui', '.json', '.qss')

        for root, dirs, files in os.walk(basedir):
            root_path = Path(root)
            try:
                dirs.remove('__pycache__')
            except ValueError:
                pass
            if root_path == basedir:
                files.remove(_EXAMPLE_CONFIG)
            files = cast(List[str], filter(is_file_allowed, files))
            bundle_files.extend(root_path / f for f in files)

        self._create_file_tabs(file_paths=bundle_files, selected=example_entrypoint, basedir=basedir)

    def _create_file_tabs(self, file_paths: List[Path], selected: str, basedir: Path):
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
            filename = file_path.relative_to(basedir)
            ext = filename.suffix
            if ext in ('.py', '.json', '.qss'):
                widget = EditorTab(file_path=file_path, file_type=ext, parent=self.tabs)
            elif ext == '.ui':
                tab = DesignerTab(file_path=file_path, parent=self.tabs)
                tab.designer_opened.connect(ExamplesWindow._open_designer_file)
                widget = tab
            filename_str = str(filename)
            self.tabs.addTab(widget, filename_str)
            if filename_str == selected:
                # Trigger display of the main file
                self.tabs.setCurrentWidget(widget)

    @staticmethod
    def _absolute_module_id(basedir: Path) -> str:
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
        rel_path = basedir.relative_to(_CURR_DIR)
        abs_mod_path.extend(rel_path.parts)
        return '.'.join(abs_mod_path)

    @staticmethod
    def _module_from_example(basedir: Path, name: str) -> Optional[types.ModuleType]:
        """
        Resolves the Python module from the directory of the example.

        Args:
            basedir: absolute path to the example.
            name: name of the example to be set for the module.

        Returns:
            Python module or None if failed to load.
        """
        if not basedir.is_dir():
            logger.warning(f'Cannot display example from {basedir} - not a directory')
            return None

        config = basedir / _EXAMPLE_CONFIG
        if not config.exists() or not config.is_file():
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
        file_path = self._selected_example_path / self._selected_example_entrypoint
        args: List[str] = ['comrad', 'run']
        if self._selected_example_args is not None:
            args.extend(self._selected_example_args)
        if '--log-level' not in args:
            # Mirror current log level to the child app (e.g. when running in DEBUG, also launch example in DEBUG)
            args.append('--log-level')
            args.append(logging.getLevelName(logging.getLogger().level))
        ExamplesWindow._turn_off_implicit_rbac_plugin(args)
        args.append(str(file_path))
        logger.debug(f'Launching app with args: {args}')
        env = dict(os.environ, PYJAPC_SIMULATION_INIT=(self._selected_example_japc_generator or ''))
        python_path = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f'{_CURR_DIR}:{python_path}'

        import subprocess
        try:
            return subprocess.run(args=args, shell=False, env=env, check=True)
        except subprocess.CalledProcessError as ex:
            logger.error(f'comrad run has failed: {str(ex)}')

    @staticmethod
    def _turn_off_implicit_rbac_plugin(input_args: List[str]):
        disable_plugins_idx: Optional[int] = None
        disable_plugins_list: Optional[List[str]] = None
        for idx, arg in enumerate(input_args):
            if arg in ['--enable-plugins', '--disable-plugins', '--nav-bar-order']:
                try:
                    plugins = input_args[idx + 1]
                except IndexError:
                    continue
                plugin_ids = [x.strip() for x in plugins.split(',')]
                if 'comrad.rbac' in plugin_ids:
                    return  # Do not modify args, comrad.rbac is explicitly participating in the example
                if arg == '--disable-plugins':
                    disable_plugins_idx = idx + 1
                    disable_plugins_list = plugin_ids
        if disable_plugins_idx is not None and disable_plugins_list is not None:
            disable_plugins_list.append('comrad.rbac')
            input_args[disable_plugins_idx] = ','.join(disable_plugins_list)
        else:
            input_args.extend(['--disable-plugins', 'comrad.rbac'])

    @staticmethod
    def _open_designer_file(file_path: str):
        """Opens *.ui file in Qt Designer"""
        from _comrad.designer import run_designer
        from _comrad.comrad_info import CCDA_MAP
        run_designer(files=[file_path], ccda_env=CCDA_MAP['PRO'])


class DesignerTab(QWidget):

    designer_opened = Signal([str])
    """Fired when "Open in Designer" button is pressed."""

    def __init__(self, file_path: Path, parent: Optional[QWidget] = None):
        """
        Page for the Qt Designer view in the example details.

        Args:
            file_path: Path to the designer file.
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self._file_path = file_path
        self.designer_btn: Optional[QPushButton] = None

    def _btn_clicked(self):
        """Forwards the signal adding path information"""
        self.designer_opened.emit(str(self._file_path))

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)

        if self.designer_btn is not None:
            return

        uic.loadUi(_CURR_DIR / 'ui_details.ui', self)
        btn: QPushButton = self.designer_btn  # Remove optional, as we are sure it was set here
        btn.clicked.connect(self._btn_clicked)


class EditorTab(QWidget):

    def __init__(self, file_path: Path, file_type: str, parent: Optional[QWidget] = None):
        """
        Page for the text file editor in the example details.

        Args:
            file_path: Path to the text file.
            file_type: Type of the file to configure appropriate lexer.
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self._file_path = file_path
        self._file_type = file_type
        self.code_viewer: Optional[QAbstractScrollArea] = None

    def showEvent(self, event: QShowEvent) -> None:
        # Creates code editor when shown for the first time.
        super().showEvent(event)

        # Not a first show event
        if self.code_viewer is not None:
            return

        if _QSCI_AVAILABLE:
            editor = QsciScintilla()

            if self._file_type == '.py':
                lexer = QsciLexerPython(editor)
                editor.setLexer(lexer)
            elif self._file_type == '.json':
                lexer = QsciLexerJSON(editor)
                editor.setLexer(lexer)
            elif self._file_type == '.qss':
                lexer = QsciLexerCSS(editor)
                editor.setLexer(lexer)
            else:
                raise TypeError(f'Unsupported file extension "{self._file_type}" in editor tab')

            from comrad.qsci import configure_common_qsci
            configure_common_qsci(editor)
            editor.setReadOnly(True)
            self.code_viewer = editor
        else:
            editor = QTextEdit()
            editor.setUndoRedoEnabled(False)
            editor.setReadOnly(True)
            editor.setAcceptRichText(False)
            self.code_viewer = editor

        with self._file_path.open() as f:
            self.code_viewer.setText(f.read())

        layout = QVBoxLayout()
        layout.addWidget(self.code_viewer)
        layout.setContentsMargins(0, 0, 0, 1)
        self.setLayout(layout)


def run_browser(_: argparse.Namespace):
    """Runs the examples browser with the given command-line arguments.

    Args:
        _: parsed command line arguments
    """
    import sys
    app_args = ['ComRAD examples']
    app_args.extend(sys.argv)
    app = QApplication(app_args)
    app.setWindowIcon(icon('examples'))
    _ = ExamplesWindow()
    sys.exit(app.exec_())
