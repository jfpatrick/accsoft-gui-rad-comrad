import logging
import os
import functools
from pathlib import Path
from typing import Optional, List, Dict, Callable
from enum import IntEnum, auto
from qtpy.QtCore import Signal, QObject
from pyrbac import AuthenticationClient, AuthenticationError, Token
from comrad._cwm_utils import parse_cmw_error_message


logger = logging.getLogger(__name__)


class CRBACLoginStatus(IntEnum):
    LOGGED_OUT = 0
    LOGGED_IN_BY_LOCATION = 1
    LOGGED_IN_BY_CREDENTIALS = 2


class CRBACStartupLoginPolicy(IntEnum):
    LOGIN_BY_LOCATION = auto()
    LOGIN_BY_CREDENTIALS = auto()
    NO_LOGIN = auto()


class CRBACState(QObject):

    rbac_logout_user = Signal()
    """Emits request to control system layer to perform a logout."""

    rbac_status_changed = Signal(int)
    """Emits when authentication of the user has been changed."""

    rbac_token_changed = Signal(list, int)
    """
    Notifies when a new token has been obtained. First argument is the serialized token (array of bytes),
    second = login status as in :class:`CRBACLoginStatus`.
    """

    rbac_error = Signal(str, bool)
    """Emits when authentication error occurs. First argument is the message string and a boolean
       for request type (``True`` -> by location, ``False`` -> by username)"""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._status = CRBACLoginStatus.LOGGED_OUT
        self.user: Optional[str] = None
        self.startup_login_policy = CRBACStartupLoginPolicy.LOGIN_BY_LOCATION
        self._auth_client: Optional[AuthenticationClient] = None

        # This token is used to retrieve pyrbac-specific info (not using java)
        self._last_pyrbac_token: Optional[Token] = None
        # This is used to retrieve roles (only when logging it via pyrbac. When set to None, it means that no pyrbac
        # login was used and not Role picker must be shown. This is a temporary measure, until we can use
        # LoginService from pyrbac and ditch Java login completely)
        self._all_roles: Optional[List[str]] = None

    @property
    def status(self) -> CRBACLoginStatus:
        return self._status

    @status.setter
    def status(self, new_status: CRBACLoginStatus):
        if new_status == self._status:
            return
        self._status = new_status
        logger.debug(f'RBA Status has changed to {str(new_status)}')
        self.rbac_status_changed.emit(self._status.value)

    @property
    def roles(self) -> Optional[Dict[str, bool]]:
        if self._last_pyrbac_token and self._all_roles is not None:
            active_roles = self._last_pyrbac_token.get_roles()
            return {role: role in active_roles for role in self._all_roles}
        return None

    @property
    def can_show_role_picker(self) -> bool:
        return (self._all_roles is not None and self._last_pyrbac_token is not None
                and not self._last_pyrbac_token.empty())

    def login_by_credentials(self, user: str, password: str, roles: Optional[List[str]] = None):
        self._generic_login(user,
                            password,
                            login_status=CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS,
                            login_debug_type='with credentials',
                            login_func=self._client.login_explicit,
                            roles=roles)

    def login_by_location(self, roles: Optional[List[str]] = None):
        self._generic_login(login_status=CRBACLoginStatus.LOGGED_IN_BY_LOCATION,
                            login_debug_type='by location',
                            login_func=self._client.login_location,
                            roles=roles)

    def logout(self):
        logger.debug('RBA Logout requested')
        if self.status == CRBACLoginStatus.LOGGED_OUT:
            logger.debug('RBA logout dropped, as user logged out already')
            return
        self._last_pyrbac_token = None

        # Normally this info will be back-propagated from Java after it has recreated the token, however we duplicate
        # it here because of the applications without pyjapc connections, that don't instantiate pyjapc, thus
        # it does not exist and does not participate in the login.
        if self.receivers(self.rbac_token_changed) == 0:
            self.status = CRBACLoginStatus.LOGGED_OUT
            # We don't call auth client here, as it does not have logout capability. Logout is only for LoginService

        self.rbac_logout_user.emit()

    def rbac_on_error(self, message: str, by_loc: bool):
        """Callback to receive JAPC login errors."""
        logger.warning(f'RBAC received error authenticating by {"location" if by_loc else "username"}: {message}')
        self._last_pyrbac_token = None
        self.rbac_error.emit(message, by_loc)

    def _generic_login(self,
                       *login_args,
                       login_status: CRBACLoginStatus,
                       login_debug_type: str,
                       login_func: Callable,
                       roles: Optional[List[str]] = None):
        force_relogin = roles is not None and self.status != CRBACLoginStatus.LOGGED_OUT
        if force_relogin:
            logger.debug(f'RBA Re-Login {login_debug_type} requested with roles: {roles}')
        else:
            logger.debug(f'RBA Login {login_debug_type} requested')
            if self.status != CRBACLoginStatus.LOGGED_OUT:
                logger.debug('RBA login dropped, as user logged in already')
                return

        try:
            token: Token = login_func(*login_args, functools.partial(self._on_pyrbac_login, roles_selected=roles))
        except AuthenticationError as e:
            self.rbac_on_error(message=parse_cmw_error_message(str(e)),
                               by_loc=login_status == CRBACLoginStatus.LOGGED_IN_BY_LOCATION)
            return

        self._last_pyrbac_token = token

        if force_relogin:
            # Make sure we simulate logout before so that all services can detect the change of status
            self.user = None
            self.status = CRBACLoginStatus.LOGGED_OUT
            self.rbac_logout_user.emit()

        # Normally this info will be back-propagated from Java after it has recreated the token, however we duplicate
        # it here because of the applications without pyjapc connections, that don't instantiate pyjapc, thus
        # it does not exist and does not participate in the login.
        # TODO: Remove this when Java is removed from RBAC completely
        if self.receivers(self.rbac_token_changed) == 0:
            self.user = token.get_user_name()
            self.status = login_status
        else:
            # This will communicate token to Java, and Java will update the login status later
            self.rbac_token_changed.emit(token.get_encoded(), int(login_status))

    def _on_pyrbac_login(self, roles_available: List[str], roles_selected: Optional[List[str]] = None) -> List[str]:
        self._all_roles = roles_available
        if roles_selected is None:
            # Default login without explicit roles. Select all non-critical roles.
            roles_selected = [r for r in roles_available if not is_rbac_role_critical(r)]
        logger.debug(f'RBA request roles: {roles_selected}')
        return roles_selected

    @property
    def _client(self) -> AuthenticationClient:
        if self._auth_client is None:
            self._auth_client = _get_auth_client()
        return self._auth_client


def is_rbac_role_critical(role: str) -> bool:
    """
    Check if the given role is critical (MCS)

    Args:
        role: Role name.

    Returns:
        ``True`` if it is "MCS" (critical).
    """
    # As suggested by SRC team, until pyrbac starts delivering Role objects, we have to assume that
    # critical roles are based on the naming convention.
    return role.startswith('MCS-')


def _get_auth_client() -> AuthenticationClient:
    try:
        return AuthenticationClient.create()
    except RuntimeError as e:
        if 'public key' in str(e):
            # pyrbac throws an exception, when it cannot find /user/rbac/pkey/rba-pub.txt, which is available on
            # NFS only. We bundle this key as a fallback to enable applications in environments without NFS
            here = Path(__file__).parent.absolute()
            bundled_key = str(here / 'rba-bundled-pub-key.txt')
            logger.warning(f'RBAC failed to locate public key, attempting to use bundled one from {bundled_key}')
            os.environ['RBAC_PKEY'] = bundled_key
            return AuthenticationClient.create()
        else:
            raise
