import logging
from typing import Optional, cast
from qtpy.QtWidgets import (QWidget, QToolButton, QMenu, QMessageBox,
                            QWidgetAction, QSizePolicy, QHBoxLayout, QAction)
from qtpy.QtCore import Qt, QSize
from comrad.app.application import CApplication
from comrad.rbac import CRBACLoginStatus, CRBACState
from comrad.rbac.rbac_dialog import RbaAuthDialogWidget
from comrad.rbac.role_picker import RbaRolePicker
from comrad.icons import icon
from comrad.app.plugins.common import CToolbarWidgetPlugin


logger = logging.getLogger(__name__)


class RbaButtonSet(QWidget):

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Set of buttons that assist with authentication & authorization via RBAC.

        Args:
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self._app = cast(CApplication, CApplication.instance())
        self._app.rbac.rbac_status_changed.connect(self._status_changed)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self._auto_btn = RbaAuthButton(app=self._app, parent=self)
        layout.addWidget(self._auto_btn)
        self._user_btn = RbaUserButton(rbac=self._app.rbac, parent=self)
        layout.addWidget(self._user_btn)
        self._status_changed(self._app.rbac.status)

    def _status_changed(self, new_status: int):
        status = CRBACLoginStatus(new_status)
        self._auto_btn.decorate(self._app.rbac)
        if status == CRBACLoginStatus.LOGGED_OUT:
            self._user_btn.hide()
        else:
            self._user_btn.show()
            self._user_btn.setText(self._app.rbac.user)


class RbaUserButton(QToolButton):

    def __init__(self, rbac: CRBACState, parent: Optional[QWidget] = None):
        """
        Button that is embedded into the toolbar to open the dialog.

        Args:
            rbac: Handle to the RBAC manager.
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setAutoRaise(True)
        menu = QMenu(self)
        self.setMenu(menu)
        self._rbac = rbac
        action = QAction('Select Roles', self)
        action.triggered.connect(self._open_role_picker)
        menu.addAction(action)

    def _open_role_picker(self):
        if self._rbac.can_show_role_picker:
            picker = RbaRolePicker(rbac=self._rbac, parent=self)
            # Currently role picker will notify RBAC on its own, we don't need to handle callbacks here
            picker.exec_()
        else:
            QMessageBox().information(self,
                                      'Action required',
                                      'Roles are currently not available via automatic login. Please logout and login '
                                      'again to enable the Role Picker.',
                                      QMessageBox.Ok)


class RbaAuthButton(QToolButton):

    def __init__(self, app: CApplication, parent: Optional[QWidget] = None):
        """
        Button that is embedded into the toolbar to open the dialog.

        Args:
            app: Application object holding RBAC handler.
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setIconSize(QSize(24, 24))
        self.setAutoRaise(True)
        self.setPopupMode(QToolButton.InstantPopup)
        self._menu = QMenu(self)
        action = QWidgetAction(self)
        action.setDefaultWidget(RbaAuthDialogWidget(parent=self, app=app))
        self._menu.addAction(action)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.decorate(rbac=app.rbac)

    def decorate(self, rbac: CRBACState):
        """
        Decorate the button in accordance with the RBAC status.

        Args:
            rbac: RBAC object controlling the status and routing login/logout requests.
        """
        icon_name: str
        if rbac.status == CRBACLoginStatus.LOGGED_OUT:
            icon_name = 'offline'
            self.setMenu(self._menu)
            try:
                self.clicked.disconnect()
            except TypeError:
                # Was not connected (happens during initial setup)
                pass
        else:
            icon_name = 'online'
            menu = self.menu()
            if menu:  # Avoid initial error, when menu might not be created
                menu.hide()
            self.setMenu(None)
            self.clicked.connect(rbac.logout)

        self.setIcon(icon(icon_name))


class RbaToolbarPlugin(CToolbarWidgetPlugin):
    """Plugin to display RBAC button in the toolbar."""

    position = CToolbarWidgetPlugin.Position.RIGHT
    plugin_id = 'comrad.rbac'
    gravity = 999

    def create_widget(self):
        return RbaButtonSet()
