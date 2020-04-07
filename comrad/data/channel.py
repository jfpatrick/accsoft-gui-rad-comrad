import logging
from typing import Callable, Optional, cast, Any, Generic, TypeVar, Dict
from dataclasses import dataclass
from qtpy.QtCore import Signal
from pydm.widgets.channel import PyDMChannel
from comrad.monkey import modify_in_place, MonkeyPatchedClass
from comrad.generics import GenericMeta


logger = logging.getLogger(__name__)


_ENABLE_CONNECTIONS: bool = True


def allow_connections(enable: bool):
    """
    Enables/disables automatic connection of the newly created channels. This is useful to disable when we want to
    modify the channel, before PyDM gets a chance to connect it to data plugins.
    """
    global _ENABLE_CONNECTIONS
    logger.debug(f'Toggling PyDM connections: {enable}')
    _ENABLE_CONNECTIONS = enable


@modify_in_place
class CChannel(PyDMChannel, MonkeyPatchedClass):

    def __init__(self,
                 *args,
                 request_signal: Optional[Signal] = None,
                 request_slot: Optional[Callable[[Any, str], None]] = None,
                 **kwargs):
        """
        Monkey-patched verion of PyDMChannel that allows proactive request for data from the control system.
        It adds requested_slot and requested_signal properties.

        Args:
            request_slot: Slot that widget provide in order to receive requested data
            request_signal: Signal from the channel instance to the connection to really request data from the control system.
        """
        self._overridden_members['__init__'](self, *args, **kwargs)
        self.request_slot = request_slot
        """Slot that receives value requested via :attr:`request_signal`.."""
        self.request_signal = request_signal
        """Signal that is issued when the channel wants to actively request new data from the control system."""

    def __eq__(self, other: object):
        """Overridden to add comparison of additional members."""
        if isinstance(self, other.__class__):
            other_obj = cast(CChannel, other)
            request_slot_matched = self.request_slot == other_obj.request_slot
            request_signal_matched = self.request_signal is None and other_obj.request_signal is None
            if self.request_signal and other_obj.request_signal:
                request_signal_matched = self.request_signal.signal == other_obj.request_signal.signal
            if not request_slot_matched or not request_signal_matched:
                return False
        return self._overridden_members['__eq__'](self, other)

    def connect(self):
        """
        Overridden method to avoid connection until we are absolutely ready. This connection can be repeated via
        :meth:`activate` call.
        """
        if not _ENABLE_CONNECTIONS:
            logger.debug(f'Preventing channel connection. Connections are temporarily disabled: {self}')
            return
        self._overridden_members['connect'](self)


T = TypeVar('T')


@dataclass
class CChannelData(Generic[T], metaclass=GenericMeta):
    """
    Container to transmit data from the control system plugins to the widgets.
    """

    value: T
    """Actual value that can be a dictionary for the whole property or a value of the data field."""

    meta_info: Dict[str, Any]
    """Meta information (or header as called by JAPC and RDA). This contains timestamps, cycle names and other related meta-information."""
