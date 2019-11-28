import logging
from typing import Optional, Tuple
from enum import IntEnum
from qtpy.QtCore import Signal, QObject


logger = logging.getLogger(__name__)


class RBACLoginStatus(IntEnum):
    LOGGED_OUT = 0
    LOGGED_IN_BY_LOCATION = 1
    LOGGED_IN_BY_CREDENTIALS = 2


class RBACStartupLoginPolicy(IntEnum):
    LOGIN_BY_LOCATION = 0
    LOGIN_BY_CREDENTIALS = 1
    NO_LOGIN = 2


class RBACState(QObject):

    rbac_login_by_location = Signal()
    """Emits request to control system layer to perform a login by location."""

    rbac_login_user = Signal(str, str)
    """Emits request to control system layer to perform a login by location."""

    rbac_logout_user = Signal()
    """Emits request to control system layer to perform a logout."""

    rbac_status_changed = Signal(int)
    """Emits when authentication of the user has been changed."""

    rbac_error = Signal(tuple)
    """Emits when authentication error occurs. Payload is a tuple of message string and a boolean
       for request type (True -> by location, False -> by username)"""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._status = RBACLoginStatus.LOGGED_OUT
        self.user: Optional[str] = None
        self.startup_login_policy = RBACStartupLoginPolicy.LOGIN_BY_LOCATION

    @property
    def status(self) -> RBACLoginStatus:
        return self._status

    @status.setter
    def status(self, new_status: RBACLoginStatus):
        if new_status == self._status:
            return
        self._status = new_status
        logger.debug(f'RBA Status has changed to {str(new_status)}')
        self.rbac_status_changed.emit(self._status.value)

    def login_by_credentials(self, user: str, password: str):
        logger.debug(f'RBA Login with credentials requested: {user}')
        if self.status != RBACLoginStatus.LOGGED_OUT:
            logger.debug('RBA login dropped, as user logged in already')
        self.rbac_login_user.emit(user, password)

    def login_by_location(self):
        logger.debug('RBA Login by location requested')
        if self.status != RBACLoginStatus.LOGGED_OUT:
            logger.debug('RBA login dropped, as user logged in already')
            return
        self.rbac_login_by_location.emit()

    def logout(self):
        logger.debug('RBA Logout requested')
        if self.status == RBACLoginStatus.LOGGED_OUT:
            logger.debug('RBA logout dropped, as user logged out already')
            return
        self.rbac_logout_user.emit()

    def rbac_on_error(self, payload: Tuple[str, bool]):
        """Callback to receive JAPC login errors."""
        message, by_loc = payload
        logger.warning(f'RBAC received error authenticating by {"location" if by_loc else "username"}: {message}')
        self.rbac_error.emit(payload)
