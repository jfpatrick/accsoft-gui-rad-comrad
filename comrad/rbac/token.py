from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from pyrbac import Token, account_type_to_string


@dataclass(eq=False, frozen=True)
class CRBACRole:
    """User's role in the control system."""

    name: str
    """Name of the role."""

    lifetime: int = -1
    """Lifetime of the role in seconds."""

    active: bool = False
    """Is role activated within current token."""

    @property
    def is_critical(self) -> bool:
        """Check if the given role is critical (MCS)."""
        # As suggested by SRC team, until pyrbac starts delivering Role objects, we have to assume that
        # critical roles are based on the naming convention.
        return _is_rbac_role_critical(self.name)

    def __eq__(self, other):
        return type(other) == type(self) and self.name == other.name


class CRBACToken:

    class Location:

        def __init__(self, token: Token):
            """
            Origin of the authentication request.

            Args:
                token: Original :mod:`pyrbac` token.
            """
            super().__init__()
            self._token = token

        @property
        def name(self) -> str:
            """Name of the authentication origin."""
            return self._token.get_location_name()

        @property
        def address(self) -> str:
            """IPv4 address of the authentication request origin."""
            return '.'.join([str(dig + 256) for dig in self._token.get_location_address()])

        @property
        def auth_required(self) -> bool:
            """Is authentication required from this location."""
            return self._token.is_location_auth_required()

    def __init__(self, original_token: Token, available_roles: List[str]):
        """
        RBAC token abstraction on ComRAD level.

        Args:
            original_token: Original :mod:`pyrbac` token.
            available_roles: All role names available for this user.
        """
        super().__init__()
        self._token = original_token
        self._all_roles = available_roles
        self._loc: Optional[CRBACToken.Location] = None
        self._roles: Optional[List[CRBACRole]] = None

    @property
    def roles(self) -> List[CRBACRole]:
        """List of all available roles."""
        if self._roles is None:
            self._roles = self._objectify_roles(token=self._token, available_roles=self._all_roles)
        return self._roles

    @property
    def username(self) -> str:
        """Username."""
        return self._token.get_user_name()

    @property
    def user_email(self) -> str:
        """Email of the user."""
        return self._token.get_user_email()

    @property
    def user_full_name(self) -> str:
        """First and last name of the user."""
        return self._token.get_full_name()

    @property
    def account_type(self) -> str:
        """Human-readable account type of the user."""
        return account_type_to_string(self._token.get_account_type())

    @property
    def valid(self) -> bool:
        """Is token valid?"""
        # According to Martin. There's currently no is_valid() API, like in Java
        return not self._token.is_token_expired()

    @property
    def empty(self) -> bool:
        """Is token empty?"""
        return self._token.empty()

    @property
    def auth_timestamp(self) -> datetime:
        """Time when authentication has happened and this token was issued."""
        return datetime.fromtimestamp(self._token.get_authentication_time())

    @property
    def expiration_timestamp(self) -> datetime:
        """Time when this token is expected to expire."""
        return datetime.fromtimestamp(self._token.get_expiration_time())

    @property
    def app_name(self) -> str:
        """Application name of the requester. This is similar but not identical to ComRAD's main window title."""
        return self._token.get_application_name()

    @property
    def location(self) -> 'CRBACToken.Location':
        """Location information of the requester."""
        if self._loc is None:
            self._loc = CRBACToken.Location(token=self._token)
        return self._loc

    @property
    def serial_id(self) -> str:
        """Serial identifier number in hexadecimal format."""
        return hex(self._token.get_serial_id())

    def _objectify_roles(self, token: Token, available_roles: List[str]):
        active_role_names = token.get_roles()
        extra_fields = token.get_extra_fields()
        if extra_fields:
            role_lifetimes = extra_fields.get_roles_lifetime()
        else:
            role_lifetimes = [-1] * len(active_role_names)
        active_roles = [CRBACRole(name=name, lifetime=lifetime, active=True)
                        for name, lifetime in zip(active_role_names, role_lifetimes)]

        def get_role_val(name: str) -> CRBACRole:
            for role in active_roles:
                if role.name == name:
                    return role
            else:
                return CRBACRole(name=name, active=False)

        return [get_role_val(role) for role in available_roles]


def _is_rbac_role_critical(role: str) -> bool:
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
