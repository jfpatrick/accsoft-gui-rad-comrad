from enum import IntEnum, auto
from dataclasses import dataclass


@dataclass
class CEnumValue:
    """
    JAPC enums are transformed into data structures with several fields so that widgets can make a weighed
    decision on how to represent the value.
    """

    class Meaning(IntEnum):
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

    code: int
    """Numeric value backing the enum option. This must be unique across all the values inside the same enum."""

    label: str
    """Label associated with the enum value. This is usually user-facing name of the value."""

    meaning: 'CEnumValue.Meaning'
    """Meaning associated with each value. This can help to visually emphasize specific options."""

    settable: bool
    """Whether the value can be sent back to the control system, or it is meant simply for display (e.g. values like
    "BUSY" or "ERROR" are meant for display and should never be set by the user."""
