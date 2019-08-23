import os
import signal
import logging
import types
import glob
import itertools
import importlib
import importlib.util
import importlib.machinery
from qtpy import uic
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QMainWindow, QApplication, QTreeWidgetItem, QTreeWidget, QStackedWidget,
                            QAbstractScrollArea, QLabel, QPushButton, QGroupBox, QSizePolicy, QVBoxLayout)
from comrad import __version__, __author__
from pydm.widgets.template_repeater import FlowLayout
from typing import List, Optional

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
    QSCI_AVAILABLE = True
except ImportError:
    QSCI_AVAILABLE = False


# Notify the kernel that we are not going to handle SIGINT
signal.signal(signal.SIGINT, signal.SIG_DFL)


logging.basicConfig()
logger = logging.getLogger(__file__)


EXAMPLE_CONFIG = '__init__.py'
EXAMPLE_DETAILS_INTRO_PAGE = 0
EXAMPLE_DETAILS_DETAILS_PAGE = 1

EXAMPLE_DETAILS_UI_PAGE = 1
EXAMPLE_DETAILS_PY_PAGE = 0


class ExamplesWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # For IDE support, assign types to dynamically created items from the *.ui file
        self.example_details: QStackedWidget = None
        self.examples_tree: QTreeWidget = None
        self.example_code_browser: QAbstractScrollArea = None
        self.example_code: QGroupBox = None
        self.example_code_stack: QStackedWidget = None
        self.example_desc_label: QLabel = None
        self.example_title_label: QLabel = None
        self.example_run_btn: QPushButton = None
        self.example_designer_btn: QPushButton = None

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'main.ui'), self)

        # If QScintilla is available, dismantle simple editor and place it instead
        if QSCI_AVAILABLE:
            par = self.example_code_browser.parentWidget()
            self.example_code_browser.deleteLater()
            self.example_code_browser = self.create_scintilla_editor()
            par.layout().addWidget(self.example_code_browser)

        self.example_file_layout = FlowLayout()
        layout: QVBoxLayout = self.example_code.layout()
        layout.insertLayout(0, self.example_file_layout)
        self.example_code.setLayout(layout)

        self._selected_example_path: str = None
        self._selected_example_entrypoint: str = None
        self._selected_source_file: str = None

        self.example_details.setCurrentIndex(EXAMPLE_DETAILS_INTRO_PAGE)

        self.actionAbout.triggered.connect(self.show_about)
        self.actionExit.triggered.connect(self.close)

        excludes = set(['_', '.'])
        example_paths: List[str] = []
        curr_dir = os.path.dirname(__file__)
        for root, dirs, files in os.walk(curr_dir):
            logger.debug(f'Entering {root}')
            is_exec = EXAMPLE_CONFIG in files
            if root != curr_dir and is_exec:
                example_paths.append(root)
                logger.debug(f'Example {root} is executable. Will stop here.')
                dirs[:] = [] # Do not go deeper, as it might simply contain submodules
            else:
                dirs[:] = [d for d in dirs if d[0] not in excludes]
                logger.debug(f'Will crawl child dirs: {dirs}')

        formatted = "\n".join(example_paths)
        logger.debug(f'Located examples in dirs:\n{formatted}')

        for path in example_paths:
            relative = os.path.relpath(path, curr_dir)
            dirs = relative.split(os.path.sep)
            parent_subtree: QTreeWidgetItem = self.examples_tree.invisibleRootItem()
            for name in dirs:
                curr_subtree: QTreeWidgetItem = None
                for idx in range(parent_subtree.childCount()):
                    child = parent_subtree.child(idx)
                    if child.text(0) == name:
                        curr_subtree = child
                        break
                if not curr_subtree:
                    curr_subtree = QTreeWidgetItem(parent_subtree, [name])
                parent_subtree = curr_subtree

        self.examples_tree.itemActivated.connect(self.on_example_selected)
        self.examples_tree.itemClicked.connect(self.on_example_selected)
        self.example_run_btn.clicked.connect(self.run_example)
        self.example_designer_btn.clicked.connect(self.open_designer_file)
        self.show()

    def show_about(self):
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

    def on_example_selected(self, item: QTreeWidgetItem, _: int):
        name = item.data(0, Qt.DisplayRole)
        # Allow selecting only leaf items
        if item.childCount() > 0:
            logger.debug(f'Ignoring selection of {name} - not a leaf element')
            return
        curr_item = item
        path_dirs = []
        while True:
            par = curr_item.parent()
            path_dirs.append(curr_item.data(0, Qt.DisplayRole))
            if not par:
                break
            curr_item = par

        path_dirs.reverse()
        example_path = os.path.join(os.path.dirname(__file__), *path_dirs)

        if self._selected_example_path == example_path:
            # Already selected. Do nothing
            return

        self._selected_example_path = example_path
        example_mod = self.load_example(basedir=example_path, name=name)
        self.display_example(module=example_mod, basedir=example_path)

    def display_example(self, module: types.ModuleType, basedir: os.PathLike):
        try:
            example_entrypoint: str = module.entrypoint
            example_title: str = module.title
            example_description: str = module.description
        except AttributeError as e:
            logger.warning(f'Cannot display example - config file is incomplete: {str(e)}')
            return

        self._selected_example_entrypoint = example_entrypoint
        self.example_title_label.setText(example_title)
        self.example_desc_label.setText(example_description)

        self.example_details.setCurrentIndex(EXAMPLE_DETAILS_DETAILS_PAGE)

        files: List[str] = list(itertools.chain.from_iterable([glob.glob(os.path.join(basedir, f'*.{ext}'))
                                                               for ext in ['py', 'ui']]))
        files = [os.path.relpath(path=p, start=basedir) for p in files]
        files.remove(EXAMPLE_CONFIG)

        self.set_file_buttons(files)

    def set_file_buttons(self, names: List[str]):
        for i in range(self.example_file_layout.count()):
            item = self.example_file_layout.itemAt(0)
            self.example_file_layout.removeItem(item)
            item.widget().deleteLater()

        first_btn = None
        for name in names:
            btn = QPushButton()
            btn.setText(name)
            btn.setCheckable(True)
            policy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            btn.setSizePolicy(policy)
            btn.clicked.connect(self.display_file)
            self.example_file_layout.addWidget(btn)
            if first_btn is None:
                first_btn = btn

        # Trigger display of the first file
        if first_btn:
            first_btn.click()

    def load_example(self, basedir: os.PathLike, name: str) -> Optional[types.ModuleType]:
        if not os.path.isdir(basedir):
            logger.warning(f'Cannot display example from {basedir} - not a directory')
            return

        config = os.path.join(basedir, EXAMPLE_CONFIG)
        if not os.path.exists(config) or not os.path.isfile(config):
            logger.warning(f'Cannot display example from {basedir} - cannot find entry point')
            return

        spec: importlib.machinery.ModuleSpec = importlib.util.spec_from_file_location(name=name, location=config)
        mod: types.ModuleType  = importlib.util.module_from_spec(spec)
        loader: importlib.machinery.SourceFileLoader = spec.loader
        try:
            loader.exec_module(mod)
        except ImportError as e:
            logger.warning(f'Cannot import example from {basedir}: {str(e)}')
            return
        return mod

    def run_example(self):
        if not self._selected_example_entrypoint or not self._selected_example_path:
            logger.warning(f'Won\'t run example. Entrypoint is undefined.')
            return

        self.run_external_app(app='comrun',
                              file_path=os.path.join(self._selected_example_path, self._selected_example_entrypoint))

    def open_designer_file(self):
        if not self._selected_source_file or not self._selected_example_path:
            logger.warning(f'Won\'t open UI file. Path information missing.')
            return
        self.run_external_app(app='comrad_designer',
                              file_path=os.path.join(self._selected_example_path, self._selected_source_file))

    def display_file(self):
        btn: QPushButton = self.sender()

        for i in range(self.example_file_layout.count()):
            push: QPushButton = self.example_file_layout.itemAt(i).widget()
            push.setChecked(push == btn)

        filename = btn.text()
        file_path = os.path.join(self._selected_example_path, filename)

        _, ext = os.path.splitext(filename)
        if ext == '.py':
            with open(file_path) as f:
                self.example_code_browser.setText(f.read())
            self.example_code_stack.setCurrentIndex(EXAMPLE_DETAILS_PY_PAGE)
        elif ext == '.ui':
            self.example_code_stack.setCurrentIndex(EXAMPLE_DETAILS_UI_PAGE)
        self._selected_source_file = filename

    def run_external_app(self, app: str, file_path: os.PathLike):
        import subprocess
        args = [app, file_path]
        try:
            return subprocess.run(args=args, shell=False, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f'{app} has failed: {str(e)}')

    def create_scintilla_editor(self):
        editor = QsciScintilla()
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
        return editor


def run():
    import sys
    if '--debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    app = QApplication(sys.argv)
    _ = ExamplesWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()