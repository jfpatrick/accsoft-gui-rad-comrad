import logging
from typing import Optional, Union, Iterable, cast
from qtpy.QtWidgets import QWidget, QMenu
from qtpy.QtCore import QCoreApplication
from pydm.pydm_ui import Ui_MainWindow
from pydm.main_window import PyDMMainWindow
from pydm.data_plugins import is_read_only
from pydm.about_pydm.about import AboutWindow
from .monkey import modify_in_place, MonkeyPatchedClass


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
        # TODO: Need a subclass of the about window with our custom layout
        AboutWindow(self).show()

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


@modify_in_place
class CUiMainWindow(Ui_MainWindow, MonkeyPatchedClass):
    """
    Monkey-patched generated UI file class to replace labels as early as
    possible to not confuse the user with naming.
    """

    def retranslateUi(self, MainWindow):
        _translate = QCoreApplication.translate
        self._overridden_methods['retranslateUi'](self, MainWindow)
        MainWindow.setWindowTitle(_translate('MainWindow', 'ComRAD Main Window'))
        self.actionAbout_PyDM.setText(_translate('MainWindow', 'About PyDM'))
