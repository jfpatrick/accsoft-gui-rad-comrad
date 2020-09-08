import logging
import base64
from typing import Optional
from enum import IntEnum, auto
from qtpy.QtCore import Signal, QObject
from pyrbac import Token
from accwidgets.rbac import RbaButtonModel, RbaToken, RbaRole


logger = logging.getLogger('comrad.rbac')


CRbaToken = RbaToken
CRbaRole = RbaRole


class CRbaLoginStatus(IntEnum):
    UNKNOWN = RbaToken.LoginMethod.UNKNOWN
    LOCATION = RbaToken.LoginMethod.LOCATION
    EXPLICIT = RbaToken.LoginMethod.EXPLICIT
    LOGGED_OUT = max(*RbaToken.LoginMethod) + 1


class CRbaStartupLoginPolicy(IntEnum):
    LOGIN_BY_LOCATION = auto()
    LOGIN_EXPLICIT = auto()
    NO_LOGIN = auto()


class CRbaState(QObject):

    login_succeeded = Signal(Token)
    """
    Fires when the login is successful, sending a newly obtained token.
    """

    login_failed = Signal(str, int)
    """
    Signal emitted when login fails. The first argument is error message, the second argument is login method value,
    that corresponds to the :class:`~accwidgets.rbac.RbaToken.LoginMethod` enum.
    """

    logout_finished = Signal()
    """Fires when the logout has been finished."""

    def __init__(self, parent: Optional[QObject] = None,
                 startup_policy: CRbaStartupLoginPolicy = CRbaStartupLoginPolicy.LOGIN_BY_LOCATION):
        super().__init__(parent)
        self._model = RbaButtonModel(parent=self)
        self._model.login_succeeded.connect(self.login_succeeded)
        self._model.login_succeeded.connect(self._on_login_succeeded)
        self._model.login_failed.connect(self.login_failed)
        self._model.login_failed.connect(self._on_login_failed)
        self._model.logout_finished.connect(self.logout_finished)
        self._model.logout_finished.connect(self._on_logout)
        self._startup_login_policy = startup_policy

    def startup_login(self, serialized_token: Optional[str] = None):
        if serialized_token is not None:
            self._model.update_token(serialized_token)
        elif self._startup_login_policy == CRbaStartupLoginPolicy.LOGIN_BY_LOCATION:
            logger.debug('Attempting login by location on startup')
            self._model.login_by_location(interactively_select_roles=False)
        elif self._startup_login_policy == CRbaStartupLoginPolicy.LOGIN_EXPLICIT:
            # TODO: Implement presenting a dialog here
            pass

    @property
    def status(self) -> CRbaLoginStatus:
        if self._model.token is None:
            return CRbaLoginStatus.LOGGED_OUT
        return CRbaLoginStatus(self._model.token.login_method)

    @property
    def token(self) -> Optional[RbaToken]:
        return self._model.token

    @property
    def serialized_token(self) -> Optional[str]:
        """
        Returns Base64-serialized token that can be passed into the subprocess.
        """
        if self._model.token is None:
            return None
        return base64.b64encode(self._model.token.get_encoded()).decode()

    def _on_login_succeeded(self, token: Token):
        logger.info(f'RBAC auth successful: {token.get_user_name()}')

    def _on_login_failed(self, err: str):
        logger.warning(f'RBAC auth failed: {err}')

    def _on_logout(self):
        logger.info(f'RBAC logout')
