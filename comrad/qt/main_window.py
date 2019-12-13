import logging
import os
import platform
import subprocess
from typing import Optional, Union, Iterable, cast
from qtpy.QtWidgets import QWidget, QMenu, QAction, QMainWindow, QFileDialog, QApplication
from qtpy.QtCore import QCoreApplication, Qt
from pydm.pydm_ui import Ui_MainWindow
from pydm.main_window import PyDMMainWindow
from pydm.data_plugins import is_read_only
from comrad.monkey import modify_in_place, MonkeyPatchedClass
from .about import AboutDialog


logger = logging.getLogger(__name__)


@modify_in_place
class CMainWindow(PyDMMainWindow, MonkeyPatchedClass):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 hide_nav_bar: bool = False,
                 hide_menu_bar: bool = False,
                 hide_status_bar: bool = False,
                 **kwargs):
        """Main window of ComRAD application.

        Args:
            parent: Parent widget of the window.
            hide_nav_bar: Hide navigation bar initially.
            hide_menu_bar: Hide menu bar initially.
            hide_status_bar: Hide status bar initially.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        self._overridden_methods['__init__'](self,
                                             parent=parent,
                                             hide_nav_bar=hide_nav_bar,
                                             hide_menu_bar=hide_menu_bar,
                                             hide_status_bar=hide_status_bar,
                                             **kwargs)
        self.ui.action_exit.triggered.connect(self.close)

    def update_window_title(self):
        """Overridden method to enable ComRAD branding."""

        if self.showing_file_path_in_title_bar:
            title = self.current_file()
        else:
            title = self._display_widget.windowTitle()
        title += ' - ComRAD'
        if is_read_only():
            title += ' [Read Only]'
        self.setWindowTitle(title)

    def show_about_window(self, _: bool):
        AboutDialog(self).show()

    def edit_in_designer(self, _: bool):
        """Overridden slot to open current file in Qt Designer and/or Text editor based on the file type."""
        ui_file, py_file = self.get_files_in_display()
        if py_file is not None and py_file != "":
            self._open_editor_generic(py_file)
        if ui_file is not None and ui_file != "":
            self._open_editor_ui(ui_file)

    def open_file_action(self, _: bool):
        """Overridden slot to open file that substitutes the name of the file type visible in the dialog."""
        modifiers = QApplication.keyboardModifiers()
        try:
            curr_file: str = self.current_file()
            folder: str = os.path.dirname(curr_file)
        except IndexError:
            folder: str = os.getcwd()

        filename = QFileDialog.getOpenFileName(self, 'Open File...', folder, 'ComRAD Files (*.ui *.py)')
        filename: str = filename[0] if isinstance(filename, (list, tuple)) else filename

        if filename:
            filename = str(filename)
            try:
                if modifiers == Qt.ShiftModifier:
                    self.app.new_window(filename)
                else:
                    self.open_file(filename)
            except (IOError, OSError, ValueError, ImportError) as e:
                self.handle_open_file_error(filename, e)

    def get_or_create_menu(self, name: Union[str, Iterable[str]]) -> QMenu:
        """Retrieves existing menu or creates a new one, if does not exist.

        Args:
            name: Name of the top level menu or chain of the submenus, starting from the top level.

        Returns:
            An existing menu or the new one, if such does not exist yet.
        """
        self._get_or_create_menu(name)

    def _get_or_create_menu(self,
                           name: Union[str, Iterable[str]],
                           parent: Optional[QMenu] = None,
                           full_path: Optional[str] = None) -> QMenu:
        parent_menu: QMenu = parent or self.menuBar()
        full_path = full_path or cast(str, name)
        if isinstance(name, str):
            try:
                menu = next((a.menu() for a in parent_menu.actions() if a.text() == name))
            except StopIteration:
                if isinstance(parent_menu, QMenu):
                    logger.debug(f'Adding new menu "{name}" to parent "{parent_menu.title()}"')
                else:
                    logger.debug(f'Adding new menu "{name}" to menu bar')
                return parent_menu.addMenu(name)
            if menu is None:
                path = full_path if isinstance(full_path, str) else '->'.join(full_path)
                raise ValueError(f'Cannot create submenu "{path}". Another action (not submenu) with '
                                 'this name already exists')
            return menu
        else:
            menu = parent_menu
            for sub_name in name:
                menu = self._get_or_create_menu(name=sub_name, parent=menu, full_path=full_path)
            return menu

    def _open_editor_ui(self, filename: str):
        """Overridden of PyDM's main_window.edit_in_designer.open_editor_ui inner method."""
        if not filename:
            return
        from _comrad.designer import run_designer
        from comrad.qt.application import CApplication
        self.statusBar().showMessage(f"Launching '{filename}' in ComRAD Designer...", 5000)
        app = cast(CApplication, QCoreApplication.instance())
        run_designer(files=[filename],
                     blocking=False,
                     ccda_env=app.ccda_endpoint,
                     use_inca=app.use_inca,
                     java_env=app.jvm_flags)

    def _open_editor_generic(self, filename: str):
        """
        We only care about Linux, but this is (more or less) a direct copy-paste of PyDM's
        main_window.edit_in_designer.open_editor_generic inner method.
        """
        system = platform.system()
        if system == "Linux":
            subprocess.call(('xdg-open', filename))
        elif system == "Darwin":
            subprocess.call(('open', filename))
        elif system == "Windows":
            os.startfile(filename)


@modify_in_place
class CUiMainWindow(Ui_MainWindow, MonkeyPatchedClass):
    """
    Monkey-patched generated UI file class to replace labels as early as
    possible to not confuse the user with naming.
    """

    def setupUi(self, MainWindow: QMainWindow):
        self.action_exit = QAction(MainWindow)
        self.action_exit.setEnabled(True)
        self.action_exit.setShortcutContext(Qt.ApplicationShortcut)
        self.action_exit.setObjectName('action_exit')
        self._overridden_methods['setupUi'](self, MainWindow)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.action_exit)

    def retranslateUi(self, MainWindow: QMainWindow):
        _translate = QCoreApplication.translate
        self._overridden_methods['retranslateUi'](self, MainWindow)
        MainWindow.setWindowTitle(_translate('MainWindow', 'ComRAD Main Window'))
        self.actionAbout_PyDM.setText(_translate('MainWindow', 'About ComRAD'))
        self.action_exit.setText(_translate('MainWindow', 'Exit'))
