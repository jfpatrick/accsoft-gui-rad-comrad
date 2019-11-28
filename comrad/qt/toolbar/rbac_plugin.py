import os
import logging
from typing import Optional, cast
from qtpy.QtWidgets import (QWidget, QPushButton, QLineEdit, QLabel, QDialog, QVBoxLayout, QToolButton, QMenu,
                            QWidgetAction, QSizePolicy)
from qtpy import uic
from qtpy.QtCore import Signal, Qt, QEvent
from comrad.qt.application import CApplication
from comrad.qt.plugin import CToolbarWidgetPlugin, CPluginPosition
from comrad.qt.rbac import RBACLoginStatus
from comrad.utils import icon


logger = logging.getLogger(__name__)


class RBACDialogWidget(QWidget):
    """Dialog seen when user presses the RBAC button."""

    login_by_location = Signal()
    login_by_username = Signal(str, str)

    def __init__(self, app: CApplication, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # For IDE support, assign types to dynamically created items from the *.ui file
        self.loc_btn: QPushButton = None
        self.user_btn: QPushButton = None
        self.username: QLineEdit = None
        self.password: QLineEdit = None
        self.user_error: QLabel = None
        self.password_error: QLabel = None
        self.loc_error: QLabel = None

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'rbac_dialog.ui'), self)

        self.user_error.hide()
        self.loc_error.hide()
        self.password_error.hide()

        self.loc_btn.clicked.connect(self._login_loc)
        self.user_btn.clicked.connect(self._login_user)

        self.login_by_location.connect(app.rbac.login_by_location)
        self.login_by_username.connect(app.rbac.login_by_credentials)
        app.rbac.rbac_status_changed.connect(self._clean_password)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonPress or event.type() == QEvent.MouseButtonRelease:
            # Prevent widget being hidden on a click inside the popup area
            return True
        return super().event(event)

    def _login_loc(self):
        self.loc_error.hide()
        self.login_by_location.emit()

    def _login_user(self):
        user = self.username.text()
        if not user:
            self.user_error.setText('You must define username')
            self.user_error.show()
        passwd = self.password.text()
        if not passwd:
            self.password_error.setText('You must define password')
            self.password_error.show()
        if not user or not passwd:
            return

        self.user_error.hide()
        self.password_error.hide()
        self.login_by_username.emit(user, passwd)

    def _clean_password(self):
        self.password.setText(None)


class RBACDialog(QDialog):

    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        layout = QVBoxLayout()
        layout.addWidget(RBACDialogWidget())
        self.setLayout(layout)


class RBACButton(QToolButton):

    def __init__(self, parent: Optional[QWidget] = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._app = cast(CApplication, CApplication.instance())
        self._dialog: Optional[RBACDialog] = None
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setPopupMode(QToolButton.InstantPopup)
        self._menu = QMenu(self)
        action = QWidgetAction(self)
        action.setDefaultWidget(RBACDialogWidget(parent=self, app=self._app))
        self._menu.addAction(action)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self._decorate(status=self._app.rbac.status)
        self._app.rbac.rbac_status_changed.connect(self._status_changed)

    def _status_changed(self, new_status: int):
        status = RBACLoginStatus(new_status)
        self._decorate(status=status)

    def _decorate(self, status: RBACLoginStatus):
        icon_name: str
        if status == RBACLoginStatus.LOGGED_OUT:
            self.setText('RBA: no token')
            icon_name = 'offline'
            self.setMenu(self._menu)
            try:
                self.clicked.disconnect()
            except TypeError:
                # Was not connected (happens during initial setup)
                pass
        else:
            self.setText(f'RBA: {self._app.rbac.user}')
            icon_name = 'online'
            menu = self.menu()
            if menu:  # Avoid initial error, when menu might not be created
                menu.hide()
            self.setMenu(None)
            self.clicked.connect(self._app.rbac.logout)

        self.setIcon(icon(icon_name, file_path=os.path.join(os.path.dirname(__file__))))

# def _clicked(self):
    #     if self._dialog:
    #         return
    #
    #     self._dialog = RBACDialog(self._app.main_window)
    #     self._dialog.show()
    #     self._dialog.exec_()
    #     self._dialog = None

# class RBACPlugin(CWidgetActionPlugin):
#
#     position = CPluginPosition.RIGHT
#     icon = 'google-plus-circle'
#
#     def create_widget(self):
#         return RBACDialogWidget()
#
#     def title(self) -> str:
#         return 'RBAC'
#
#     def triggered(self):
#         print(f'RBAC triggered')

class RBACButtonPlugin(CToolbarWidgetPlugin):

    position = CPluginPosition.RIGHT
    plugin_id = 'comrad.rbac'
    enabled = False

    def create_widget(self):
        return RBACButton()


















# from enum import Enum
# from typing import Optional, Dict, Any
# from datetime import datetime
#
#
# class LoginPolicy(Enum):
#     """The enumeration describes initial login policy applied during an application startup."""
#
#     DEFAULT = 0
#     """Default login at startup - by location, by Kerberos, then explicit."""
#
#     EXPLICIT = 1
#     """Only explicit login at startup."""
#
#     KERBEROS = 2
#     """Only Kerberos login at startup."""
#
#     LOCATION = 3
#     """Only login by location at startup."""
#
#     NO_LOGIN = 4
#     """Do not perform login at startup."""
#
#
# class TokenType(Enum):
#     """Enum which defines all possible types of tokens."""
#
#     APPLICATION = 0
#     MASTER = 1
#     LOCAL_MASTER = 2
#
#
# class RBAToken:
#
#     def __init__(self,
#                  serial_id: int,
#                  auth_time: datetime,
#                  end_time: datetime,
#                  app: str,
#                  loc: str,
#                  user: str,
#                  extra: Dict[str, Any],
#                  token_type: TokenType):
#         self.serial_id = serial_id
#         self.auth_time = auth_time
#         self.end_time = end_time
#         self.app = app
#         self.loc = loc
#         self.user = user
#         self.extra = extra
#         self.token_type = token_type
#
#
# class RBAIntegrator:
#     """RBAC integrator for ComRAD applications. Basic usage
#     # TODO: Write sample usage
#     """
#
#     def __init__(self,
#                  app_name: Optional[str] = None,
#                  initial_login_policy: LoginPolicy = LoginPolicy.DEFAULT,
#                  relogin_policy: LoginPolicy = LoginPolicy.LOCATION,
#                  show_role_picker: bool = False,
#                  show_user_label: bool = True):
#         """
#         Args:
#             app_name: parent application name.
#             initial_login_policy: initial login policy (i.e. first login) to apply after the application startup.
#             relogin_policy: relogin policy to apply when a token is about to expire.
#             show_role_picker: show role picker popup after every login.
#             show_user_label: show label with the currently logged in username.
#         """
#         self._app_name = app_name
#         self._initial_login_policy = initial_login_policy
#         self._relogin_policy = relogin_policy
#         self._show_role_picker = show_role_picker
#         self._show_user_label = show_user_label
#
#     @property
#     def current_token(self) -> RBAToken:
