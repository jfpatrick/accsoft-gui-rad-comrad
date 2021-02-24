import logging
from typing import Optional, List, cast
from qtpy.QtWidgets import (QWidget, QToolButton, QMenu, QMessageBox, QDialog,
                            QWidgetAction, QSizePolicy, QAction)
from qtpy.QtCore import Qt
from comrad.app.application import CApplication
from comrad.rbac import CRBACLoginStatus, CRBACState
from comrad.rbac.rbac_dialog import RbaAuthDialogWidget, RbaExplicitLoginDialog
from comrad.rbac.role_picker import RbaRolePicker
from comrad.rbac.token_dialog import RbaTokenDialog
from comrad.icons import icon
from comrad.app.plugins.common import CToolbarWidgetPlugin
from comrad.app._toolbtn import ToolButton, ToolButtonSet


logger = logging.getLogger('comrad.app.plugins.toolbar.rbac_plugin')


class RbaButtonSet(ToolButtonSet):

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Set of buttons that assist with authentication & authorization via RBAC.

        Args:
            parent: Parent widget to hold this object.
        """
        super().__init__(parent=parent)
        self.app.rbac.rbac_status_changed.connect(self._status_changed)
        self._status_changed(self.app.rbac.status)

    def create_buttons(self, app):
        return [
            RbaAuthButton(app=app, parent=self),
            RbaUserButton(rbac=app.rbac, parent=self),
        ]

    def _status_changed(self, new_status: int):
        status = CRBACLoginStatus(new_status)
        auth_btn, user_btn = tuple(self.buttons)
        cast(RbaAuthButton, auth_btn).decorate(self.app.rbac)
        if status == CRBACLoginStatus.LOGGED_OUT:
            user_btn.hide()
        else:
            user_btn.show()
            user_btn.setText(self.app.rbac.user)


class RbaUserButton(ToolButton):

    def __init__(self, rbac: CRBACState, parent: Optional[QWidget] = None):
        """
        Button that is embedded into the toolbar to open the dialog.

        Args:
            rbac: Handle to the RBAC manager.
            parent: Parent widget to hold this object.
        """
        super().__init__(parent=parent,
                         track_style=False,
                         track_icon_size=False,
                         horizontal=QSizePolicy.Preferred,
                         vertical=QSizePolicy.Expanding)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setAutoRaise(True)
        menu = QMenu(self)
        self.setMenu(menu)
        self._rbac = rbac
        act_roles = QAction('Select Roles', self)
        act_roles.triggered.connect(self._open_role_picker)
        menu.addAction(act_roles)
        menu.addSeparator()
        act_token = QAction('Show Existing RBAC Token', self)
        act_token.triggered.connect(self._open_token_details)
        menu.addAction(act_token)

    def _open_role_picker(self):
        token = self._rbac.token
        if token is not None:
            picker = RbaRolePicker(roles=token.roles, parent=self)
            picker.roles_selected.connect(self._on_roles_selected)
            picker.exec_()
        else:
            QMessageBox().information(self,
                                      'Action required',
                                      'Roles are currently not available via automatic login. Please logout and login '
                                      'again to enable the Role Picker.',
                                      QMessageBox.Ok)

    def _on_roles_selected(self, selected_roles: List[str], role_picker: QDialog):
        # For some reason self.sender() gives handle to self here, so we have to pass role_picker explicitly in signal

        if self._rbac.status == CRBACLoginStatus.LOGGED_IN_BY_LOCATION:
            self._rbac.login_by_location(preselected_roles=selected_roles)
            # Since we were logged in by location before, assumption is that it will succeed again, not much
            # else we can ask user to do. In corner cases it may fail though.
            # It is better though to avoid ephemeral signal connection to close dialog after successful re-login,
            # as this connection may stay alive.
            role_picker.accept()

        elif self._rbac.status == CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS:
            # Note! This is a workaround (cause we can't re-login again without storing user's credentials),
            # We must ask for login again.

            if self._rbac.user is None:
                raise RuntimeError('Unexpectedly username is missing but status indicates successful explicit login')

            dialog = RbaExplicitLoginDialog(new_roles=selected_roles, username=self._rbac.user, parent=self)
            dialog.setWindowTitle('Authenticate to apply new roles')
            if dialog.exec_() == QDialog.Accepted:
                logger.debug('Closing role picker after successful login')
                role_picker.accept()

    def _open_token_details(self):
        token = self._rbac.token
        if token is not None:
            dialog = RbaTokenDialog(token=token, parent=self)
            dialog.exec_()
        else:
            QMessageBox().information(self,
                                      'Action required',
                                      'Token information is currently not available via automatic login. Please '
                                      'logout and login again to view token details.',
                                      QMessageBox.Ok)


class RbaAuthButton(ToolButton):

    def __init__(self, app: CApplication, parent: Optional[QWidget] = None):
        """
        Button that is embedded into the toolbar to open the dialog.

        Args:
            app: Application object holding RBAC handler.
            parent: Parent widget to hold this object.
        """
        super().__init__(parent=parent,
                         track_style=False,
                         horizontal=QSizePolicy.Preferred,
                         vertical=QSizePolicy.Expanding)
        self.setAutoRaise(True)
        self.setPopupMode(QToolButton.InstantPopup)
        self._menu = TabFocusPreservingMenu(self)
        action = QWidgetAction(self)
        action.setDefaultWidget(RbaAuthDialogWidget(parent=self, app=app))
        # rba_widget = RbaAuthDialogWidget(parent=self, app=app)
        # action.setDefaultWidget(rba_widget)
        # rba_widget.setFocusPolicy(Qt.TabFocus)
        # rba_widget.setFocusProxy(rba_widget.tabs)
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

    def create_widget(self, _):
        return RbaButtonSet()


class TabFocusPreservingMenu(QMenu):
    """
    Subclass that restores default Tab behavior.

    As explained `here <https://stackoverflow.com/a/20388856>`__, menus have a special treatment
    of Tab keystrokes, mainly to navigate up and down the menu. However, we want to preserve Tab
    navigation within out login widget, otherwise jumping between Username/Password fields is
    inconvenient.
    """

    def focusNextPrevChild(self, next: bool) -> bool:
        """
        Finds a new widget to give the keyboard focus to, as appropriate for ``Tab`` and ``Shift+Tab``,
        and returns ``True`` if it can find a new widget, or ``False`` if it can't.

        If ``next`` is ``True``, this function searches forward, if ``next`` is ``False``, it searches backward.

        Sometimes, you will want to reimplement this function. For example, a web browser might reimplement it to
        move its "current active link" forward or backward, and call :meth:`QWidget.focusNextPrevChild` only when
        it reaches the last or first link on the "page".

        Child widgets call :meth:`QWidget.focusNextPrevChild` on their parent widgets, but only the window that
        contains the child widgets decides where to redirect focus. By reimplementing this function for an object,
        you thus gain control of focus traversal for all child widgets.
        """
        return QWidget.focusNextPrevChild(self, next)
