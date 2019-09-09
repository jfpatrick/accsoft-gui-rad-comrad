from typing import Optional
from enum import Enum
from qtpy.QtCore import Signal, QObject

class RBACLoginStatus(Enum):
    LOGGED_OUT = 0
    LOGGED_IN_BY_LOCATION = 1
    LOGGED_IN_BY_CREDENTIALS = 2


class RBACState(QObject):

    rbac_status_changed = Signal()
    """Emits when authentication of the user has been changed."""

    def __init__(self):
        self.status = RBACLoginStatus.LOGGED_OUT
        self.user: Optional[str] = None
