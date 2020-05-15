import logging
from typing import Optional, cast, List, Iterable
from qtpy.QtCore import Property
from qtpy.QtWidgets import QWidget
from pydm.widgets.base import PyDMWidget
from comrad.monkey import modify_in_place, MonkeyPatchedClass
from comrad.data.channel import PyDMChannel, CChannel, format_address
from comrad.data.context import CContext, find_context_provider, CContextTrackingDelegate


logger = logging.getLogger(__name__)


def common_widget_repr(self: QWidget) -> str:
    """
    Common implementation of :meth:`object.__repr__` for :class:`QWidget`-derived objects that may have a
    :meth:`QWidget.objectName`.

    Args:
        self: object reference.

    Returns:
        Formatted string.
    """
    prefix = f'<{type(self).__name__} at {hex(id(self))}'
    obj_name = self.objectName()
    if not obj_name:
        return prefix + '>'
    return f'{prefix} ({obj_name})>'


@modify_in_place
class CWidget(PyDMWidget, MonkeyPatchedClass):

    def __init__(self, init_channel: Optional[str] = None):
        self._local_context: Optional[CContext] = None  # Keep a copy so we can locate old channel addresses when updating
        self._channel_ids: List[str] = []
        self._overridden_members['__init__'](self)  # Do not pass init_channel here, we'll set it in showEvent
        self._context_tracker = CContextTrackingDelegate(self)
        logger.debug(f'{self}: Installing new context tracking event handler: {self._context_tracker}')
        cast(QWidget, self).installEventFilter(self._context_tracker)
        if init_channel:
            self._channel_ids.append(init_channel)

    def create_channel(self, channel_address: str, context: Optional[CContext]) -> CChannel:
        """
        Factory to create channels. This can be overridden in case there is a need to connect channels differently.

        Args:
            channel_address: Original device/property(#field) address that user types in.
            context: Context for selector and/or data filters that should influence the connection.

        Returns:
            Newly created channel.
        """
        ch = cast(CChannel, PyDMChannel(address=channel_address,
                                        connection_slot=self.connectionStateChanged,
                                        value_slot=self.channelValueChanged,
                                        value_signal=None,
                                        write_access_slot=None))
        if hasattr(self, 'writeAccessChanged'):
            ch.write_access_slot = self.writeAccessChanged
        if hasattr(self, 'send_value_signal'):
            ch.value_signal = self.send_value_signal
        ch.context = context
        return ch

    def reconnect(self, new_ch_addresses: List[str], new_context: Optional[CContext]):
        """
        Method that updates existing connections with the new ones.

        Args:
            new_ch_addresses: New channel addresses to connect to.
            new_context: New context assisting the connection.
        """
        swap_all = new_context != self._local_context
        channels_to_add: Iterable[str]
        if swap_all:
            channels_to_add = new_ch_addresses
            channels_to_remove = [format_address(ch, self._local_context) for ch in self._channel_ids]
        else:
            new_channels = set(new_ch_addresses)
            old_channels = set(self._channel_ids)
            zombie_channels = {ch for ch in self._channels if not ch.connected}  # We have to try to reconnect these
            channels_to_add = new_channels.difference(old_channels).union(zombie_channels)
            channels_to_remove = [format_address(ch, self._local_context) for ch in old_channels.difference(new_channels)]

        for channel in list(self._channels):  # Avoid iterator change during the mutation inside loop body
            if channel.address not in channels_to_remove:
                continue
            channel.disconnect()
            self._channels.remove(channel)

        self._channel_ids = new_ch_addresses

        if not self._context_tracker.context_ready:
            # In case the widget belongs inside a CContextContainer, we want to have the connection only after
            # the widget is displayed, because then we can be fairly sure that we get a correct context.
            logger.debug(f'Not creating channels for widget {self} because context is not ready yet')
            return

        self._local_context = CContext.from_existing_replacing(new_context) if new_context else None

        # Create new connection
        if not channels_to_add:
            return

        for ch in channels_to_add:
            channel = self.create_channel(ch, new_context)
            channel.connect()
            self._channels.append(channel)

    def _set_context(self, new_val: Optional[CContext]):
        if new_val != self._local_context:
            filters_changed = bool((not new_val and self._local_context and self._local_context.data_filters)
                                   or (not self._local_context and new_val and new_val.data_filters)
                                   or (new_val and self._local_context
                                       and (new_val.data_filters != self._local_context.data_filters)))
            selector_changed = bool((not new_val and self._local_context and self._local_context.selector)
                                    or (not self._local_context and new_val and new_val.selector)
                                    or (new_val and self._local_context
                                        and (new_val.selector != self._local_context.selector)))
            if filters_changed or selector_changed:
                logger.debug(f'New context has selector or data filters changed. This will trigger re-connecting channel on {self}')
                self.reconnect(self._channel_ids, new_val)
            elif not self._channels:
                logger.debug(f'Attempting to make new connections on {self}')
                self.reconnect(self._channel_ids, new_val)
            else:
                # In the upper condition this assignment happens inside "reconnect"
                self._local_context = CContext.from_existing_replacing(new_val) if new_val else None

    context = property(fget=lambda self: self._local_context, fset=_set_context)
    """
    Context that widget operates on. This context will be attached to all the channels so they
    can pass the information into the control system adapter.
    """

    def context_changed(self):
        """
        Slot that receives a new context from the context provider, (e.g. when widgets are grouped inside a container).

        Args:
            new_val: New context
        """
        context_provider = find_context_provider(self)
        if context_provider:
            self.context = context_provider.get_context_view()
        else:
            self.context = None

    __repr__ = common_widget_repr


def _factory_channel_setter(self: CWidget, new_val: Optional[str]):
    if (new_val or None) != (self._channel or None):  # Equalize '' and None
        set_val = [new_val] if new_val else []
        self.reconnect(set_val, self._local_context)


def _channel_getter(self: CWidget) -> Optional[str]:
    # For compatibility with PyDM, as it expects the instance attribute there
    try:
        return self._channel_ids[0]
    except IndexError:
        return None


PyDMWidget.channel = Property(str, fget=PyDMWidget.channel.fget, fset=_factory_channel_setter)
PyDMWidget._channel = property(fget=_channel_getter, fset=lambda *_: None)
