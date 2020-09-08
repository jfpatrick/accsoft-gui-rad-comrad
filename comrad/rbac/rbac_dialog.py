import logging
from typing import Optional, List, cast
from pathlib import Path
from qtpy import uic
from qtpy.QtCore import QEvent, QSignalBlocker, Qt
from qtpy.QtWidgets import (QWidget, QPushButton, QLineEdit, QLabel, QTabWidget, QCheckBox, QVBoxLayout,
                            QDialogButtonBox, QDialog)
from comrad.app.application import CApplication
from comrad.rbac import CRBACLoginStatus


logger = logging.getLogger(__name__)


_TAB_LOCATION_LOGIN = 0
_TAB_EXPLICIT_LOGIN = 1


class RbaAuthDialogWidget(QWidget):

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
        self.roles_explicit: QCheckBox = None
        self.roles_loc: QCheckBox = None

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

        self._immediate_roles: bool = False

        self.loc_btn.clicked.connect(self._login_loc)
        self.user_btn.clicked.connect(self._login_user)

        if roles is None:
            logging.debug('Enabling role picking at login')
            self.roles_explicit.stateChanged.connect(self._roles_change)
            self.roles_loc.stateChanged.connect(self._roles_change)
        else:
            # Roles already have been preselected, so we don't give user an opportunity to pick them here
            logging.debug('Disabling role picking at login')
            self.roles_explicit.hide()
            self.roles_loc.hide()

        self._roles = roles

        app.rbac.rbac_status_changed.connect(self._clean_password)
        app.rbac.rbac_error.connect(self._on_error)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonPress or event.type() == QEvent.MouseButtonRelease:
            # Prevent widget being hidden on a click inside the popup area
            return True
        return super().event(event)

    def _roles_change(self, state: Qt.CheckState):
        blocker1 = QSignalBlocker(self.roles_explicit)
        blocker2 = QSignalBlocker(self.roles_loc)
        self._immediate_roles = state == Qt.Checked
        self.roles_explicit.setChecked(self._immediate_roles)
        self.roles_loc.setChecked(self._immediate_roles)
        blocker1.unblock()
        blocker2.unblock()

    def _login_loc(self):
        self.loc_error.hide()
        self.user_error.hide()

        app = cast(CApplication, CApplication.instance())

        if self._immediate_roles:
            app.rbac.login_by_location(select_roles=True)
        else:
            app.rbac.login_by_location(preselected_roles=self._roles)

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

            app = cast(CApplication, CApplication.instance())

            if self._immediate_roles:
                app.rbac.login_by_credentials(user=user, password=passwd, select_roles=True)
            else:
                app.rbac.login_by_credentials(user=user, password=passwd, preselected_roles=self._roles)
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


class RbaExplicitLoginDialog(QDialog):

    def __init__(self, new_roles: List[str], username: str, parent: Optional[QWidget] = None):
        """
        Wrapper for the :class:`comrad.rbac.rbac_dialog.RbaAuthDialogWidget`. Currently, we cannot re-login
        with new roles, as :mod:`pyrbac` does not provide such capability. Instead, we are bound to ask
        the user to login again with a new login dialog.

        Args:
            new_roles: Roles to use when signing in again.
            username: Username to prefill for convenience.
            parent: Owning object.
        """
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        self.setLayout(layout)
        app = cast(CApplication, CApplication.instance())
        self._main_widget = RbaAuthDialogWidget(app=app,
                                                parent=self,
                                                initial_username=username,
                                                initial_login_strategy=app.rbac.status,
                                                roles=new_roles)
        self._main_widget.layout().setContentsMargins(0, 0, 0, 0)
        self._main_widget.tabs.removeTab(0)  # Remove Login By Location tab
        self._btn_box = QDialogButtonBox(QDialogButtonBox.Cancel, self)
        layout.addWidget(self._main_widget)
        layout.addWidget(self._btn_box)
        self._btn_box.rejected.connect(self.close)
        app.rbac.rbac_status_changed.connect(self._on_rbac_status_changed)

    def _on_rbac_status_changed(self, new_status: int):
        if new_status != CRBACLoginStatus.LOGGED_OUT:
            logger.debug('RBAC has connected, closing the login dialog')
            self.accept()
