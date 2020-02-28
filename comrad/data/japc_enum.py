from typing import Tuple
from enum import IntEnum, auto


class SimpleValueStandardMeaning(IntEnum):
    ON = auto()
    """The equipment is ON/enabled."""
    OFF = auto()
    """The equipment is OFF/disabled."""
    WARNING = auto()
    """There is a non-blocking situation worth knowing about."""
    ERROR = auto()
    """There is a problem with the controlled equipment or the control chain."""
    NONE = auto()
    """There is no standard meaning associated with the value. This is the default value."""


JapcEnum = Tuple[int, str, SimpleValueStandardMeaning, bool]
