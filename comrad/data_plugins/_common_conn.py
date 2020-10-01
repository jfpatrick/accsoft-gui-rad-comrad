import logging
import functools
import numpy as np
from typing import Optional, Any, Callable, List
from abc import abstractmethod
from qtpy.QtCore import Signal, Slot, Qt, QVariant, QObject
from comrad.generics import GenericQObjectMeta
from ._conn import CDataConnection, CChannelData, CChannel


logger = logging.getLogger('comrad.data_plugins')


class CCommonDataConnection(CDataConnection, metaclass=GenericQObjectMeta):

    requested_value_signal = Signal(CChannelData, str)
    """Similar to :attr:`~CDataConnection.new_value_signal`, but issued only on active (user-initiated) requests (or initial get)."""

    def __init__(self, channel: CChannel, address: str, protocol: Optional[str] = None, parent: Optional[QObject] = None):
        """
        Connection that is tailored to work with common control system API, relying on common operations:

        - GET
        - SET
        - SUBSCRIBE

        This is a generalized class, and independent of implementation. Thus it can be used for
        JAPC, RDA or similar APIs.

        Args:
            channel: Initial channel to connect to the data source.
            address: Address string of the device to be connected to.
            protocol: Protocol representation. Should be ``your-protocol://``.
            parent: Optional parent owner.
        """
        super().__init__(channel=channel, address=address, protocol=protocol, parent=parent)
        self._subscribe_callback = functools.partial(self._notify_listeners, callback_signals=[self.new_value_signal])

    @abstractmethod
    def get(self, callback: Callable):
        """
        Single shot GET request.

        It must always be asynchronous, returning the result in the supplied callback.

        Args:
            callback: Callback for asynchronous GET operation.
        """
        pass

    @abstractmethod
    def set(self, value: Any):
        """
        Single shot SET request.

        It must always be asynchronous. No feedback is provided about the course of the operation.

        Args:
            value: New value to set in the control system.
        """
        pass

    @abstractmethod
    def subscribe(self, callback: Callable):
        """
        Create and start subscriptions to any data source related to this connection.

        Args:
            callback: Callback for each new value from the subscription.
        """
        pass

    @abstractmethod
    def unsubscribe(self):
        """
        Stop and clear all existing subscriptions to any data source related to this connection.
        """
        pass

    @abstractmethod
    def process_incoming_value(self, *args, **kwargs) -> CChannelData[Any]:
        """
        Convert incoming raw control-system data types into ComRAD's internal data structures.
        :class:`.CChannelData` can store both actual data and its meta data. Raise an exception, if the
        data cannot be processed for some reason.

        Args:
            *args: Any positional arguments given by the control system.
            **kwargs: Any keyword arguments given by the control system.

        Returns:
            Packaged data structure.

        Raises:
             ValueError: Data cannot be packaged correctly.
        """
        pass

    def request_value(self, initiator_uid: str):
        """
        Request value from the control system after user has interactively issued the request.

        This can happen with certain widgets, e.g. :class:`~comrad.CPropertyEdit` that contains a "Get" button
        forcing the update from the control system. Default implementation issues a regular GET request.

        Default implementation performs a GET request asynchronously.

        Args:
            initiator_uid: Unique identifier of the requesting widget. It is necessary to distinguish the receiver, when
                           only one widget out of many has requested the new value, and only it should care about the
                           incoming reply.
        """
        self.get(callback=functools.partial(self._on_requested_get, initiator_uid=initiator_uid))

    def add_listener(self, channel: CChannel):
        super().add_listener(channel)
        self._connect_request_signals(channel)

        # Start receiving values
        if channel.value_slot is not None:
            if not self.connected:
                logger.debug(f'{self}: First connection and value_slot available. Will initiate subscriptions.')
                self.subscribe(callback=self._subscribe_callback)
            else:
                logger.debug(f'{self}: This was an additional listener. Initiating a single GET '
                             'to update the displayed value')
                # Artificially emit a single value to allow the UI update once because subscription
                # is not initiated here, thus we are not getting initial values
                self.get(callback=self._on_async_get)
        elif channel.request_slot is not None:
            if not self.connected:
                # If no previous listeners were added, but we are not expecting to subscribe, still subscribe, because
                # future listeners which will connect to the object will fail to receive updates
                # FIXME: This is not very straightforward. How can we fix it?
                logger.debug(f'{self}: First connection and request_slot available. Will initiate subscriptions.')
                self.subscribe(callback=self._subscribe_callback)
            else:
                logger.debug(f'{self}: This was an additional listener. Initiating a single GET '
                             f'to update the displayed value via request_slot')
                # Artificially emit a single value to allow the UI update once because subscription
                # is not initiated here, thus we are not getting initial values
                self.get(callback=self._on_requested_get)
        else:
            # Value is never to be received (for instance on buttons that work with commands)
            # We still need to notify the system that we are "connected"
            self.connected = True

    def remove_listener(self, channel: CChannel, destroying: bool = False):
        if not destroying:
            if channel.request_signal is not None:
                try:
                    channel.request_signal.disconnect(self.request_value)
                    logger.debug(f'Disconnected request_signal ({channel.request_signal}) from {self}')
                except TypeError:
                    pass

            if channel.request_slot is not None:
                try:
                    self.requested_value_signal.disconnect(channel.request_slot)
                    logger.debug(f'{self}: Disconnected requested_value_signal from {channel.request_slot}')
                except (KeyError, TypeError):
                    pass
        super().remove_listener(channel=channel, destroying=destroying)

    @Slot(str)
    @Slot(bool)
    @Slot(int)
    @Slot(float)
    @Slot(QVariant)
    @Slot(np.ndarray)
    def write_value(self, new_val: Any):
        self.set(new_val)

    def close(self):
        logger.debug(f'{self}: Stopping and removing subscriptions')
        self.unsubscribe()
        super().close()

    def _connect_request_signals(self, channel: CChannel):
        if channel.request_signal is not None:
            channel.request_signal.connect(slot=self.request_value, type=Qt.QueuedConnection)
            logger.debug(f'{self}: Connected request_signal to proactively GET')
        if channel.request_slot is not None:
            try:
                self.requested_value_signal.connect(slot=channel.request_slot, type=Qt.QueuedConnection)
            except (KeyError, TypeError):
                pass
            logger.debug(f'{self}: Connected requested_value_signal to {channel.request_slot}')

    def _on_async_get(self, *args, **kwargs):
        logger.debug(f'{self}: Received async GET callback')
        self._notify_listeners(*args, callback_signals=[self.new_value_signal], **kwargs)

    def _on_requested_get(self, *args, initiator_uid: Optional[str] = None, **kwargs):
        logger.debug(f'{self}: Received GET callback on request')

        def emit_signals(sig: Signal, value: CChannelData[Any]):
            sig.emit(value, initiator_uid)

        self._notify_listeners(*args, callback_signals=[self.requested_value_signal], emitter=emit_signals, **kwargs)

    def _notify_listeners(self, *args,
                          callback_signals: List[Signal],
                          emitter: Optional[Callable[[Signal, CChannelData[Any]], None]] = None,
                          **kwargs):
        # In case the very first value arrives on subscription, and this is the earliest indicator that our
        # connection has succeeded
        self.connected = True

        try:
            packet = self.process_incoming_value(*args, **kwargs)
        except ValueError as e:
            logger.warning(f'{self}: {str(e)}')
            return

        for signal in callback_signals or []:
            try:
                if emitter is None:
                    signal.emit(packet)
                else:
                    emitter(signal, packet)
            except (KeyError, TypeError):
                logger.warning(f'{self}: Cannot propagate received value ({type(packet.value)}) to the widget.')
