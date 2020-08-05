from typing import Optional, List
from pathlib import Path
from qtpy import uic
from qtpy.QtCore import Signal, QEvent
from qtpy.QtWidgets import QWidget, QPushButton, QLineEdit, QLabel, QTabWidget
from comrad.app.application import CApplication
from comrad.rbac import CRBACLoginStatus


_TAB_LOCATION_LOGIN = 0
_TAB_EXPLICIT_LOGIN = 1


class RbaAuthDialogWidget(QWidget):

    login_by_location = Signal([], [list])
    """Is emitted when user desires to login by location. Optional parameter is the list of roles to be used."""

    login_by_username = Signal([str, str], [str, str, list])
    """
    Is emitted when user attempts to use username/password pair to login.
    Optional third parameter is the list of roles to be used.
    """

    def __init__(self,
                 app: CApplication,
                 parent: Optional[QWidget] = None,
                 initial_username: Optional[str] = None,
                 initial_login_strategy: Optional[CRBACLoginStatus] = None,
                 roles: Optional[List[str]] = None):
        """
        Dialog seen when user presses the RBAC button.

        Args:
            app: Reference to the application instance.
            parent: Parent widget to own this object.
            initial_username: If for some reason, the used username was known, prefill it for convenience.
            initial_login_strategy: Tab to be initially open.
            roles: Roles that should be used during the login.
        """
        super().__init__(parent)

        # For IDE support, assign types to dynamically created items from the *.ui file
        self.loc_btn: QPushButton = None
        self.user_btn: QPushButton = None
        self.username: QLineEdit = None
        self.password: QLineEdit = None
        self.user_error: QLabel = None
        self.loc_error: QLabel = None
        self.tabs: QTabWidget = None

        uic.loadUi(Path(__file__).parent / 'rbac_dialog.ui', self)

        self.user_error.hide()
        self.loc_error.hide()

        if initial_username is not None:
            self.username.setText(initial_username)
            self.username.setEnabled(False)
            self.password.setFocus()
        if initial_login_strategy == CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS:
            self.tabs.setCurrentIndex(_TAB_EXPLICIT_LOGIN)
        elif initial_login_strategy == CRBACLoginStatus.LOGGED_IN_BY_LOCATION:
            self.tabs.setCurrentIndex(_TAB_LOCATION_LOGIN)

        self.loc_btn.clicked.connect(self._login_loc)
        self.user_btn.clicked.connect(self._login_user)

        self._roles = roles

        if roles is not None:
            self.login_by_location[list].connect(app.rbac.login_by_location)
            self.login_by_username[str, str, list].connect(app.rbac.login_by_credentials)
        else:
            self.login_by_location.connect(app.rbac.login_by_location)
            self.login_by_username.connect(app.rbac.login_by_credentials)
        app.rbac.rbac_status_changed.connect(self._clean_password)
        app.rbac.rbac_error.connect(self._on_error)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonPress or event.type() == QEvent.MouseButtonRelease:
            # Prevent widget being hidden on a click inside the popup area
            return True
        return super().event(event)

    def _login_loc(self):
        self.loc_error.hide()
        self.user_error.hide()
        if self._roles is not None:
            self.login_by_location[list].emit(self._roles)
        else:
            self.login_by_location.emit()

    def _login_user(self):
        user = self.username.text()
        passwd = self.password.text()
        if not user and not passwd:
            self.user_error.setText('You must type in username and password')
        elif not user:
            self.user_error.setText('You must type in username')
        elif not passwd:
            self.user_error.setText('You must type in password')
        else:
            self.user_error.hide()
            self.loc_error.hide()
            if self._roles is not None:
                self.login_by_username[str, str, list].emit(user, passwd, self._roles)
            else:
                self.login_by_username.emit(user, passwd)
            return
        self.user_error.show()

    def _clean_password(self):
        self.password.setText(None)

    def _on_error(self, msg: str, by_loc: bool):
        if by_loc:
            self.loc_error.setText(msg)
            self.tabs.setCurrentIndex(_TAB_LOCATION_LOGIN)
            self.loc_error.show()
            self.user_error.hide()
        else:
            self.user_error.setText(msg)
            self.tabs.setCurrentIndex(_TAB_EXPLICIT_LOGIN)
            self.user_error.show()
            self.loc_error.hide()
