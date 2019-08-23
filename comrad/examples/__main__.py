import os
import signal
import logging
import types
import importlib
import importlib.util
import importlib.machinery
from qtpy import uic
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QMainWindow, QApplication, QTreeWidgetItem, QTreeWidget, QStackedWidget,
                            QTextBrowser, QLabel, QPushButton, QFrame)
from comrad import __version__, __author__
from typing import List, Optional


# Notify the kernel that we are not going to handle SIGINT
signal.signal(signal.SIGINT, signal.SIG_DFL)


logging.basicConfig()
logger = logging.getLogger(__file__)


EXAMPLE_ENTRYPOINT = '__init__.py'
EXAMPLE_DETAILS_INTRO_PAGE = 0
EXAMPLE_DETAILS_DETAILS_PAGE = 1


class ExamplesWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'main.ui'), self)

        # For IDE support, assign types to dynamically created items from the *.ui file
        self.example_details: QStackedWidget
        self.examples_tree: QTreeWidget
        self.example_code_browser: QTextBrowser
        self.example_code: QFrame
        self.example_desc_label: QLabel
        self.example_title_label: QLabel
        self.example_run_btn: QPushButton

        size_policy = self.example_code.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        self.example_code.setSizePolicy(size_policy)

        self.example_details.setCurrentIndex(EXAMPLE_DETAILS_INTRO_PAGE)

        self.actionAbout.triggered.connect(self.show_about)
        self.actionExit.triggered.connect(self.close)

        excludes = set(['_', '.'])
        example_paths: List[str] = []
        curr_dir = os.path.dirname(__file__)
        for root, dirs, files in os.walk(curr_dir):
            logger.debug(f'Entering {root}')
            is_exec = EXAMPLE_ENTRYPOINT in files
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
        self.show()

    def show_about(self):
        dialog = uic.loadUi(os.path.join(os.path.dirname(__file__), 'about.ui'))
        dialog.version_label.setText(str(__version__))
        dialog.support_label.setText(__author__)
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
        example_mod = self.load_example(basedir=example_path, name=name)
        self.display_example(example_mod)

    def display_example(self, module: types.ModuleType):
        try:
            example_entrypoint: str = module.entrypoint
            example_title: str = module.title
            example_description: str = module.description
        except AttributeError as e:
            logger.warning(f'Cannot display example - config file is incomplete: {str(e)}')
            return
        example_code: Optional[str]
        try:
            example_code = module.source_code
        except AttributeError:
            example_code = None

        self.example_title_label.setText(example_title)
        self.example_desc_label.setText(example_description)
        self.example_code.setHidden(not example_code)
        if example_code:
            self.example_code_browser.setText(example_code)

        self.example_details.setCurrentIndex(EXAMPLE_DETAILS_DETAILS_PAGE)

    def load_example(self, basedir: str, name: str) -> Optional[types.ModuleType]:
        if not os.path.isdir(basedir):
            logger.warning(f'Cannot display example from {basedir} - not a directory')
            return

        config = os.path.join(basedir, EXAMPLE_ENTRYPOINT)
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


def run():
    import sys
    if '--debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    app = QApplication(sys.argv)
    _ = ExamplesWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()