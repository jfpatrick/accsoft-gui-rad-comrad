import logging
from typing import Callable, Optional, cast, Any, Generic, TypeVar, Dict
from dataclasses import dataclass
from qtpy.QtCore import Signal
from pydm.widgets.channel import PyDMChannel, clear_channel_address
from comrad.monkey import modify_in_place, MonkeyPatchedClass
from comrad.generics import GenericMeta
from .context import CContext


logger = logging.getLogger(__name__)


@modify_in_place
class CChannel(PyDMChannel, MonkeyPatchedClass):

    def __init__(self,
                 *args,
                 request_signal: Optional[Signal] = None,
                 request_slot: Optional[Callable[[Any, str], None]] = None,
                 context: Optional[CContext] = None,
                 **kwargs):
        """
        Monkey-patched verion of PyDMChannel that allows proactive request for data from the control system.
        It adds requested_slot and requested_signal properties.

        Args:
            request_slot: Slot that widget provide in order to receive requested data
            request_signal: Signal from the channel instance to the connection to really request data from the control system.
        """
        self.request_slot = request_slot
        """Slot that receives value requested via :attr:`request_signal`.."""
        self.request_signal = request_signal
        """Signal that is issued when the channel wants to actively request new data from the control system."""
        self._context: Optional[CContext] = None
        self._overridden_members['__init__'](self, *args, **kwargs)
        self.context = context

    def __eq__(self, other: object):
        """Overridden to add comparison of additional members."""
        if isinstance(self, other.__class__):
            other_obj = cast(CChannel, other)
            if self.request_slot != other_obj.request_slot:
                return False
            request_signal_matched = self.request_signal is None and other_obj.request_signal is None
            if self.request_signal and other_obj.request_signal:
                request_signal_matched = self.request_signal.signal == other_obj.request_signal.signal
            if not request_signal_matched:
                return False
        return self._overridden_members['__eq__'](self, other)

    def _get_address(self):
        """
        Overridden getter to embed selector and data filter information into the address, so that
        separate connection instances are created when these parameters differ, because differentiation happens
        by channel address.
        """
        return format_address(self._address, self._context)

    address = property(fget=_get_address, fset=PyDMChannel.address.fset)

    def _set_context(self, new_val: Optional[CContext]):
        # Need a copy to avoid dynamically changing channel address when context attribute is changed
        # Channel will need to be explicitly disconnected and another channel will have to be created
        # by an external actor
        self._context = CContext.from_existing_replacing(new_val) if new_val is not None else None

    context = property(fget=lambda self: self._context, fset=_set_context)
    """Context that may influence how data is retrieved from the channel."""

    @property
    def address_no_ctx(self) -> str:
        """Address of the channel excluding context information."""
        return self._address


def format_address(channel_address: str, context: Optional[CContext]) -> str:
    """
    Formats address for internal representation that contains all the information about requested access point,
    including device, property, field, cycle selector and data filter. This is combined in a single string,
    because PyDM groups connections by their address string, and we cannot work with multiple selectors/data filters
    through the same connection object.

    Args:
        channel_address: Device/property(#field) address.
        context: Additional context containing timing user / cycle selector / data filters.

    Returns:
        Formatter string with all information embedded.
    """
    clean_address = clear_channel_address(channel_address)
    if context:
        return clean_address + CContext.to_string_suffix(data_filters=context.data_filters, selector=context.selector)
    return clean_address


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
