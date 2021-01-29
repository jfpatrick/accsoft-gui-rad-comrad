"""
ComRAD Examples browser is a tool to browse through sources and run interactive examples
how to use ComRAD ecosystem.
"""

import logging
import types
import argparse
from subprocess import Popen
from pathlib import Path
from typing import List, Optional, Tuple, Union, cast
from qtpy import uic
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QShowEvent, QCloseEvent
from qtpy.QtWidgets import (QMainWindow, QTreeWidgetItem, QTreeWidget, QStackedWidget, QTabWidget, QApplication,
                            QAbstractScrollArea, QLabel, QPushButton, QVBoxLayout, QWidget, QTextEdit, QFrame)
from pydm.utilities.iconfont import IconFont
from comrad.icons import icon
from comrad.app.about import AboutDialog
from _comrad_examples import examples as eg

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciLexerJSON, QsciLexerCSS
    _QSCI_AVAILABLE = True
except ImportError:
    _QSCI_AVAILABLE = False


logger = logging.getLogger(__name__)


_EXAMPLE_DETAILS_INTRO_PAGE = 0
_EXAMPLE_DETAILS_DETAILS_PAGE = 1
_SUPPORTED_EDITOR_FILES = [*eg.SUPPORTED_EXT]
_SUPPORTED_EDITOR_FILES.remove('.ui')


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
        self._running_example: Optional[Popen] = None
        self._running_designer: Optional[Popen] = None

        self.alert_icon_lbl.setPixmap(IconFont().icon('exclamation-triangle').pixmap(self.alert_icon_lbl.minimumSize()))
        self.arg_frame.hide()

        self.example_details.setCurrentIndex(_EXAMPLE_DETAILS_INTRO_PAGE)

        self.actionAbout.triggered.connect(self._show_about)
        self.actionExit.triggered.connect(self.close)

        examples = eg.find_runnable()

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

    def closeEvent(self, event: QCloseEvent):
        self._kill_running_example_if_needed()
        self._kill_running_designer_if_needed()
        super().closeEvent(event)

    def _show_about(self):
        """
        Opens 'About' dialog.
        """
        AboutDialog(parent=self, icon=self.windowIcon()).show()

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
        example_mod = eg.module(basedir=example_path, name=name)
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
        try:
            title, desc, entrypoint, fgen_symbol, extra_args = eg.read(module=module, basedir=basedir)
        except AttributeError as ex:
            logger.warning(str(ex))
            return

        self._selected_example_japc_generator = fgen_symbol
        self._selected_example_entrypoint = entrypoint
        self._selected_example_args = extra_args
        self.example_title_label.setText(title)
        self.example_desc_label.setText(desc)

        self.example_details.setCurrentIndex(_EXAMPLE_DETAILS_DETAILS_PAGE)

        if extra_args:
            self.arg_frame.show()
            self.arg_lbl.setText('\n'.join(extra_args))
        else:
            self.arg_frame.hide()

        self._create_file_tabs(file_paths=eg.get_files(basedir), selected=entrypoint, basedir=basedir)

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

            if ext in _SUPPORTED_EDITOR_FILES:
                widget = EditorTab(file_path=file_path, file_type=ext, parent=self.tabs)
            elif ext == '.ui':
                tab = DesignerTab(file_path=file_path, parent=self.tabs)
                tab.designer_opened.connect(self._open_designer_file)
                widget = tab
            else:
                raise ValueError(f'Unsupported file type: {ext}')
            filename_str = str(filename)
            self.tabs.addTab(widget, filename_str)
            if filename_str == selected:
                # Trigger display of the main file
                self.tabs.setCurrentWidget(widget)

    def _run_example(self):
        """Opens runtime application for the example."""
        if not self._selected_example_entrypoint or not self._selected_example_path:
            logger.warning("Won't run example. Entrypoint is undefined.")
            return

        cmd_args, cmd_env = eg.make_cmd(entrypoint=self._selected_example_entrypoint,
                                        example_path=self._selected_example_path,
                                        japc_generator=self._selected_example_japc_generator,
                                        extra_args=self._selected_example_args)

        # FIXME: This hack should be gone when acc-py distro is fixed
        # This is related to PyQt5 failing to load due to libstdc++ incompatibility in Acc-Py
        # Under certain conditions, where another library gets loaded before PyQt5 and triggers
        # loading of libstdc++, also it does not have RPATH setup to point to Acc-Py, it will
        # cause older libstdc++ loaded, that breaks due to lack of symbols needed for PyQt5.
        # In this particular case, it's papc that is loaded from sitecustomize.py that loads
        # datetime that loads libstdc++ before PyQt5 is loaded.
        # See https://issues.cern.ch/browse/ACCPY-588 for more details
        if 'ACC_PY_PREFIX' in cmd_env:
            logger.debug('Patching environment for Acc-Py libstdc++')
            import pathlib
            gcc_libs = str(pathlib.Path(cmd_env['ACC_PY_PREFIX']).absolute() / 'gcc' / 'lib64')
            cmd_env['LD_LIBRARY_PATH'] = gcc_libs + ':' + cmd_env.get('LD_LIBRARY_PATH', '')

        self._kill_running_example_if_needed()
        self._running_example = Popen(args=cmd_args, shell=False, env=cmd_env)

    def _kill_running_example_if_needed(self):
        if self._running_example is not None:
            self._running_example.kill()
            self._running_example = None

    def _kill_running_designer_if_needed(self):
        if self._running_designer is not None:
            self._running_designer.kill()
            self._running_designer = None

    def _open_designer_file(self, file_path: str):
        """Opens *.ui file in Qt Designer"""
        from _comrad.designer import run_designer
        from _comrad.comrad_info import CCDA_MAP

        self._kill_running_designer_if_needed()
        self._running_designer = cast(Popen, run_designer(files=[file_path],
                                                          blocking=False,
                                                          ccda_env=CCDA_MAP['PRO'],
                                                          log_level=logging.getLevelName(logging.getLogger().level)))


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
