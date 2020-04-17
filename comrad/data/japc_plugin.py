import logging
import numpy as np
import functools
from pydm.data_plugins import is_read_only
from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from qtpy.QtCore import Qt, QObject, Slot, Signal, QVariant
from typing import Any, Optional, Callable, List, Dict
from comrad.data.channel import CChannel, CChannelData
from comrad.data.addr import ControlEndpointAddress
from comrad.data.pyjapc_patch import CPyJapc


logger = logging.getLogger(__name__)


_japc: Optional[CPyJapc] = None


SPECIAL_FIELDS = {
    'acqStamp': 'acqStamp',
    'setStamp': 'setStamp',
    'cycleStamp': 'cycleStamp',
    'cycleName': 'selector',
    # This is not supported for now,
    # as this bitmask is separated into several booleans by JAPC.
    # It is not advised to query this field and I should report anyone
    # Who decides to do so.
    # 'updateFlags': ???
}
"""
Special fields defined by FESA which are meta-information and will be packaged in the header of RDA or JAPC message.
Thus they should be accessed in the header and not main data block. Unfortunately, there's difference between FESA
names and JAPC, thus we need a map of what to request vs what to retrieve.
"""


def get_japc() -> CPyJapc:
    """
    Method to retrieve a singleton of the JAPC service instance.

    It is done to avoid multiple log-in attempts when having several channels working with JAPC.

    Returns:
        Singleton instance.
    """

    global _japc
    if _japc is None:
        _japc = CPyJapc()
    return _japc


class CJapcConnection(PyDMConnection):

    new_value_signal = Signal([CChannelData],  # this overload will be default (when emit is used without key)
                              # Needed here to not fail .connect() in PyDMConnection super methods
                              [int],
                              [float],
                              [str],
                              [np.ndarray])
    """Overrides superclass signal to implement only override - tuple that contains values and headers."""

    requested_value_signal = Signal(CChannelData, str)
    """Similar to new_value_signal, but issued only on active requests (or initial get)."""

    def __init__(self, channel: CChannel, address: str, protocol: Optional[str] = None, parent: Optional[QObject] = None, *args, **kwargs):
        """
        Connection serves one or multiple listeners that communicate with JAPC protocol by directing the calls into
        PyJapc API.

        Args:
            channel: Initial channel to connect to the PyJapc.
            address: Address string of the device to be connected to.
            protocol: Protocol representation. Should be japc://.
            parent: Optional parent owner.
            *args: Any additional arguments needed by :class:`~pydm.data_plugins.plugin.PyDMConnection`.
            **kwargs: Any additional keyword arguments needed by :class:`~pydm.data_plugins.plugin.PyDMConnection`
        """
        super().__init__(channel=channel,
                         address=address,
                         protocol=protocol,
                         parent=parent,
                         *args,
                         **kwargs)

        self._meta_field: Optional[str] = None
        self._subscriptions_active: bool = False
        self._selector: Optional[str] = None
        self._japc_additional_args: Dict[str, Any] = {}
        self._some_subscriptions_failed: bool = False
        self._pyjapc_param_name: str = ''
        self._repr_name = channel.address
        self._is_property_level: bool = False

        if not ControlEndpointAddress.validate_parameter_name(channel.address_no_ctx):
            # Extra protection so that selector comes from the context and not directly from the address string
            logger.error(f'Cannot create connection with invalid parameter name format "{channel.address_no_ctx}"!')
            return

        japc_address = ControlEndpointAddress.from_string(channel.address)

        if japc_address is None:
            logger.error(f'Cannot create connection for address "{channel.address}"!')
            return

        self._meta_field = (japc_address.field
                            if japc_address.field and japc_address.field in SPECIAL_FIELDS
                            else None)

        if self._meta_field:
            japc_address.field = None  # We need to request property itself and then get its header
        if japc_address.selector:
            self._japc_additional_args['timingSelectorOverride'] = self._selector = japc_address.selector
            japc_address.selector = None  # This is passed separately to PyJapc
        if japc_address.data_filters:
            # Normal parsing of data filters from string will always result in their types being strings,
            # but we must preserve original types because otherwise it can cause FESA error.
            # We still need to be able to parse data filters from string, because otherwise constructing
            # ControlEndpointAddress with unknown addition will fail the regex.
            self._japc_additional_args['dataFilterOverride'] = channel.context.data_filters
            japc_address.data_filters = None  # This is passed separately to PyJapc

        self._is_property_level = not japc_address.field

        japc_address.data_filters = None
        self._pyjapc_param_name = str(japc_address)

        self._on_subscribe_device_property = functools.partial(self._notify_listeners, callback_signals=[self.new_value_signal])
        get_japc().japc_status_changed.connect(self._on_japc_status_changed)
        self.add_listener(channel)

    def add_listener(self, channel: CChannel):
        """
        Adds a listener to the connection.

        Listener is a channel that mediates the data between widgets and PyJapc, by passing widget's signals and slots
        to be connected to :class:`CJapcConnection`.

        Args:
            channel: A new listener.
        """
        if not self._pyjapc_param_name:
            logger.error('Connection is not initialized. Will not add a listener.')
            return

        logger.debug(f'Adding a listener for {self}')
        super().add_listener(channel)
        self._connect_extra_signal_types(channel)

        if channel.value_signal is not None:
            logger.debug(f'{self}: Connecting value_signal to write into CS')
            self._connect_write_slots(channel.value_signal)
        if channel.request_signal is not None:
            channel.request_signal.connect(slot=self._requested_get, type=Qt.QueuedConnection)
            logger.debug(f'{self}: Connected request_signal to proactively GET')
        if channel.request_slot is not None:
            try:
                self.requested_value_signal.connect(slot=channel.request_slot, type=Qt.QueuedConnection)
            except (KeyError, TypeError):
                pass
            logger.debug(f'{self}: Connected requested_value_signal to {channel.request_slot}')

        # Allow write to all widgets by default. Write permissions are defined in CCDB,
        # which pyjapc does not have access to, so we can't know if a property is writable at the moment
        # TODO: This should be considering CCDA
        enable_write_access = not is_read_only()
        logger.debug(f'{self}: Emitting write access: {enable_write_access}')
        self.write_access_signal.emit(enable_write_access)

        # Issue a connection signal (e.g. if it's an additional listener for already connected channel, we need to let
        # it know that we are already connected
        self.connection_state_signal.emit(self.online)

        # Start receiving values
        if channel.value_slot is not None:
            if not self.online:
                logger.debug(f'{self}: First connection and value_slot available. Will initate subscriptions.')
                self._create_subscription()
            else:
                logger.debug(f'{self}: This was an additional listener. Initiating a single GET '
                             f'to update the displayed value')
                # Artificially emit a single value to allow the UI update once because subscription
                # is not initiated here, thus we are not getting initial values
                self._single_get(callback=self._on_async_get)
        elif channel.request_slot is not None:
            if not self.online:
                # If no previous listeners were added, but we are not expecting to subscribe, still subscribe, because
                # future listeners which will connect to the object will fail to receive updates
                # FIXME: This is not very straghtforward. How can we fix it?
                logger.debug(f'{self}: First connection and request_slot available. Will iniate subscriptions.')
                self._create_subscription()
            else:
                logger.debug(f'{self}: This was an additional listener. Initiating a single GET '
                             f'to update the displayed value via request_slot')
            # Artificially emit a single value to allow the UI update once because subscription
            # is not initiated here, thus we are not getting initial values
            self._single_get(callback=self._on_requested_get)
        else:
            # Value is never to be received (for instance on buttons that work with commands)
            # We still need to notify the system that we are "connected"
            self.online = True

    def remove_listener(self, channel: CChannel, destroying: bool = False):
        # Superclass does not implement signal for bool values
        if not destroying:
            logger.debug(f'{self}: Removing one of the listeners')
            if channel.value_slot is not None:
                try:
                    self.new_value_signal.disconnect(channel.value_slot)
                    logger.debug(f'{self}: Disconnected new_value_signal from {channel.value_slot}')
                except (KeyError, TypeError):
                    pass

            if channel.value_signal is not None:
                try:
                    channel.value_signal.disconnect(self._on_set_device_property)
                    logger.debug(f'Disconnected value_signal ({channel.value_signal}) from {self}')
                except (TypeError):
                    pass
                for data_type in [str, bool, int, float, QVariant, np.ndarray]:
                    try:
                        channel.value_signal[data_type].disconnect(self._on_set_device_property)
                        logger.debug(f'Disconnected value_signal[{data_type.__name__}] ({channel.value_signal}) from {self}')
                    except (KeyError, TypeError):
                        continue

            if channel.request_signal is not None:
                try:
                    channel.request_signal.disconnect(self._requested_get)
                    logger.debug(f'Disconnected request_signal ({channel.request_signal}) from {self}')
                except TypeError:
                    pass

            if channel.request_slot is not None:
                try:
                    self.requested_value_signal.disconnect(channel.request_slot)
                    logger.debug(f'{self}: Disconnected requested_value_signal from {channel.request_slot}')
                except (KeyError, TypeError):
                    pass

        else:
            logger.debug(f'{self}: Destroying the connection. All listeners should be disconnected automatically.')
        super().remove_listener(channel=channel, destroying=destroying)
        logger.debug(f'{self}: Listener count now is {self.listener_count}')

    def close(self):
        logger.debug(f'{self}: Closing connection, stopping and removing any JAPC subscriptions')
        get_japc().clearSubscriptions(parameterName=self._pyjapc_param_name,
                                      selector=self._selector)
        self.online = False
        super().close()

    def _on_async_get(self, _, value: Any, headerInfo: Dict[str, Any]):

        logger.debug(f'{self}: Received async GET callback')
        self._notify_listeners(parameterName=self._pyjapc_param_name, value=value, headerInfo=headerInfo, callback_signals=[
            self.new_value_signal,
        ])

    def _on_requested_get(self, _, initial_value: Any, header: Dict[str, Any], uuid: Optional[str] = None):
        logger.debug(f'{self}: Received GET callback on request')

        def emit_signals(sig: Signal, value: CChannelData[Any]):
            sig.emit(value, uuid)

        self._notify_listeners(parameterName=self._pyjapc_param_name, value=initial_value, headerInfo=header, callback_signals=[
            self.requested_value_signal,
        ], signal_handle=emit_signals)

    def _connect_extra_signal_types(self, channel: CChannel):
        # Superclass does not implement signal for some types that we use
        if channel.value_slot is not None:
            try:
                self.new_value_signal.connect(channel.value_slot, Qt.QueuedConnection)
            except (KeyError, TypeError):
                pass
            logger.debug(f'{self}: Connected new_value_signal to {channel.value_slot}')

    def _connect_write_slots(self, signal: Signal):
        set_slot_connected: bool = False
        for data_type in [str, bool, int, float, QVariant, np.ndarray]:
            try:
                signal[data_type].connect(slot=self._on_set_device_property, type=Qt.QueuedConnection)
            except (KeyError, TypeError):
                continue
            logger.debug(f'Connected write_signal[{data_type.__name__}] to {self}')
            set_slot_connected = True

        if not set_slot_connected:
            try:
                signal.connect(slot=self._on_device_command, type=Qt.QueuedConnection)
                logger.debug(f'Connected write_signal to {self}')
            except (KeyError, TypeError):
                pass

    def _notify_listeners(self,
                          parameterName: str,
                          value: Any,
                          headerInfo: Dict[str, Any],
                          signal_handle: Optional[Callable[[Signal, CChannelData[Any]], None]] = None,
                          callback_signals: Optional[List[Signal]] = None):
        del parameterName  # Unused argument (https://google.github.io/styleguide/pyguide.html#214-decision)

        self.online = True

        if self._meta_field is not None:
            # We are looking inside header instead of the value, because user has requested
            # data from a "special" field, which is a meta-field that is placed in header on the transport level
            reply_key = SPECIAL_FIELDS[self._meta_field]
            try:
                value = headerInfo[reply_key]
            except KeyError:
                logger.warning(f'{self}: Cannot locate meta-field "{self._meta_field}" inside packet header ({headerInfo}).')
                return
        elif self._is_property_level and isinstance(value, dict):
            # To not put logic of resolving "special" fields into widgets that work with the whole property,
            # we populate meta fields into the property, like if it was data
            for request_key, reply_key in SPECIAL_FIELDS.items():
                try:
                    meta_val = headerInfo[reply_key]
                except KeyError:
                    continue
                value[request_key] = meta_val

        packet = CChannelData[Any](value=value, meta_info=headerInfo)

        for signal in callback_signals or []:
            try:
                if signal_handle is not None:
                    signal_handle(signal, packet)
                else:
                    signal.emit(packet)
            except (KeyError, TypeError):
                logger.warning(f'{self}: Cannot propagate JAPC value ({type(value)}) to the widget.')

    @Slot()
    def _on_device_command(self):
        get_japc().setParam(parameterName=self._pyjapc_param_name,
                            parameterValue={},
                            **self._japc_additional_args)

    @Slot(str)
    @Slot(bool)
    @Slot(int)
    @Slot(float)
    @Slot(QVariant)
    @Slot(np.ndarray)
    def _on_set_device_property(self, new_val: Any):
        get_japc().setParam(parameterName=self._pyjapc_param_name,
                            parameterValue=new_val,
                            **self._japc_additional_args)

    @property
    def online(self) -> bool:
        return self._subscriptions_active

    @online.setter
    def online(self, connected: bool):
        self.connected = connected
        if self._subscriptions_active != connected:
            self._subscriptions_active = connected
            logger.debug(f'{self} is {"online" if connected else "offline"}')
            self.connection_state_signal.emit(connected)

    def _create_subscription(self):
        japc = get_japc()
        logger.debug(f'{self}: Subscribing to JAPC')
        japc.subscribeParam(parameterName=self._pyjapc_param_name,
                            onValueReceived=self._on_subscribe_device_property,
                            onException=self._on_subscription_exception,
                            getHeader=True,  # Needed for meta-fields
                            noPyConversion=False,
                            **self._japc_additional_args)
        self._start_subscriptions()

    # FIXME: This class needs massive refactoring
    def _requested_get(self, uuid: str):
        self._single_get(callback=functools.partial(self._on_requested_get, uuid=uuid))

    def _single_get(self, callback: Optional[Callable[[str, Any, Dict[str, Any]], None]] = None):
        japc = get_japc()
        if callback is None:
            callback = self._on_requested_get
        japc.getParam(parameterName=self._pyjapc_param_name,
                      onValueReceived=callback,
                      getHeader=True,  # Needed for meta-fields
                      noPyConversion=False,
                      **self._japc_additional_args)

    def _start_subscriptions(self):
        logger.debug(f'{self}: Starting subscriptions')
        try:
            get_japc().startSubscriptions(parameterName=self._pyjapc_param_name, selector=self._selector)
        except Exception as e:
            # TODO: Catch more specific Jpype errors here
            logger.exception(f'Unexpected error while subscribing to {self.address}'
                             '. Please verify the parameters and make sure the address is in the form'
                             f"'{self.protocol}:///device/property#field@selector' or"
                             f"'{self.protocol}:///device/prop#field' or"
                             f"'{self.protocol}:///device/property'. Underlying problem: {str(e)}")

    def _on_subscription_exception(self, param_name: str, _: str, exception: Exception):
        logger.exception(f'Exception {type(exception).__name__} triggered '  # type: ignore
                         f'on {param_name}: {exception.getMessage()}')
        self._some_subscriptions_failed = True

    def _on_japc_status_changed(self, logged_in: bool):
        if logged_in and (not self.online or self._some_subscriptions_failed):
            logger.debug(f'{self}: Reviving blocked subscriptions after login')
            self._some_subscriptions_failed = False
            # Need to stop subscriptions before restarting, otherwise they will not start
            get_japc().stopSubscriptions(parameterName=self._pyjapc_param_name, selector=self._selector)
            self._start_subscriptions()

    def __repr__(self):
        return f'<{type(self).__name__}[{self._repr_name}] at {hex(id(self))}>'


class JapcPlugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "japc://" scheme.
    """

    protocol = 'japc'
    connection_class = CJapcConnection


class Rda3Plugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rda3://" scheme.
    """

    protocol = 'rda3'
    connection_class = CJapcConnection


class Rda2Plugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rda://" scheme.
    """

    protocol = 'rda'
    connection_class = CJapcConnection


class TgmPlugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "tgm://" scheme.
    """

    protocol = 'tgm'
    connection_class = CJapcConnection


class NoPlugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "no://" scheme.
    """

    protocol = 'no'
    connection_class = CJapcConnection


class RmiPlugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rmi://" scheme.
    """

    protocol = 'rmi'
    connection_class = CJapcConnection
