import logging
from pathlib import Path
from typing import Optional, cast, Tuple
from qtpy.QtWidgets import (QWidget, QPushButton, QLineEdit, QLabel, QToolButton, QMenu,
                            QWidgetAction, QSizePolicy, QTabWidget)
from qtpy import uic
from qtpy.QtCore import Signal, Qt, QEvent
from comrad.app.application import CApplication
from comrad.rbac import CRBACLoginStatus
from comrad.icons import icon
from comrad.app.plugins.common import CToolbarWidgetPlugin


logger = logging.getLogger(__name__)


class RBACDialogWidget(QWidget):

    login_by_location = Signal()
    """Is emitted when user desires to login by location."""

    login_by_username = Signal(str, str)
    """Is emitted when user attempts to use username/password pair to login."""

    def __init__(self, app: CApplication, parent: Optional[QWidget] = None):
        """
        Dialog seen when user presses the RBAC button.

        Args:
            app: Reference to the application instance.
            parent: Parent widget to own this object.
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

        self.loc_btn.clicked.connect(self._login_loc)
        self.user_btn.clicked.connect(self._login_user)

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
            self.login_by_username.emit(user, passwd)
            return
        self.user_error.show()

    def _clean_password(self):
        self.password.setText(None)

    def _on_error(self, payload: Tuple[str, bool]):
        msg, by_loc = payload
        if by_loc:
            self.loc_error.setText(msg)
            self.tabs.setCurrentIndex(0)
            self.loc_error.show()
            self.user_error.hide()
        else:
            self.user_error.setText(msg)
            self.tabs.setCurrentIndex(1)
            self.user_error.show()
            self.loc_error.hide()


class RBACButton(QToolButton):

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Button that is embedded into the toolbar to open the dialog.

        Args:
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self._app = cast(CApplication, CApplication.instance())
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
        status = CRBACLoginStatus(new_status)
        self._decorate(status=status)

    def _decorate(self, status: CRBACLoginStatus):
        icon_name: str
        if status == CRBACLoginStatus.LOGGED_OUT:
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

        self.setIcon(icon(icon_name))


class RBACButtonPlugin(CToolbarWidgetPlugin):
    """Plugin to display RBAC button in the toolbar."""

    position = CToolbarWidgetPlugin.Position.RIGHT
    plugin_id = 'comrad.rbac'
    gravity = 999

    def create_widget(self):
        return RBACButton()
