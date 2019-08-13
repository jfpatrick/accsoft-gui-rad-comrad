import logging
import pyjapc
import datetime
import numpy as np
from pydm.data_plugins import plugin, is_read_only
from qtpy.QtCore import Qt, QObject, Slot, Signal, QVariant
from typing import Any, Optional, Union
from collections import namedtuple

# Unfortunately, we cannot import
# from pydm.widgets import channel OR
# from pydm.widgets.channel import PyDMChannel
# because it crashes with error "unable to import is_qt_designer"
# We need this import purely for typings. Therefore, we make a local stub
class channel:
    class PyDMChannel:

        value_signal: Optional[Signal]
        value_slot: Optional[Slot]

        def connect(self):
            pass

        def disconnect(self, destroying=False):
            pass


class _JapcService(pyjapc.PyJapc):
    """Singleton instance to avoid RBAC login for multiple Japc connections."""

    def __init__(self,
                 selector: str,
                 incaAcceleratorName: str,
                 noSet: bool = False,
                 timeZone: Union[str, datetime.tzinfo] = 'utc',
                 logLevel: int = None,
                 *args,
                 **kwargs):
        super().__init__(selector=selector,
                         incaAcceleratorName=incaAcceleratorName,
                         noSet=noSet,
                         timeZone=timeZone,
                         logLevel=logLevel,
                         *args,
                         **kwargs)
        self._loggedIn: bool = False

    def try_rbac_login(self):
        """
        Attempts to login by location first and only then uses RBAC dialog if required.

        This method sets internal login state to avoid repeated login attempts in the future.
        """

        # Avoid multiple login attempts
        if self._loggedIn:
            return
        try:
            self.rbacLogin()
        except Exception:
            self.log.info('RBAC login without credentials failed. Trying to connect with a dialog...')
            self.rbacLogin(loginDialog=True)
        self._loggedIn = True

    def rbacLogout(self):
        if self._loggedIn:
            super().rbacLogout()
            self._loggedIn = False

    def setParam(self, *args, **kwargs):
        if not self._loggedIn:
            self.log.warning('Cannot set param because RBAC was not passed previously')
        else:
            super().setParam(*args, **kwargs)

    def stopSubscriptions(self, parameterName: str = None, selector: str = None):
        super().stopSubscriptions(parameterName=parameterName, selector=selector)
        if not self._subscriptionHandleDict:
            self.log.info(f'Last subscription was removed from JAPC. Logging out.')
            self.rbacLogout()


_japc: Optional[_JapcService] = None


def get_japc() -> _JapcService:
    """
    Method to retrieve a singleton of the JAPC service instance.

    It is done to avoid multiple log-in attempts when having several channels working with JAPC.

    Returns:
        Singleton instance.
    """

    # Selector is important to set, otherwise the default PyJapc selector tends to be LHC.USER.ALL
    # which fails to read data from private virtual devices.
    # When passing selector, it is important to set incaAcceleratorName, because default 'auto' name
    # will try to infer the accelerator from the selector and will fail, if we are passing None
    global _japc
    if _japc is None:
        _japc = _JapcService(selector='', incaAcceleratorName='')
    return _japc


class _JapcConnection(plugin.PyDMConnection):
    """ PyDM adaptation for JAPC protocol. """

    # Superclass does not implement signal for bool values
    new_value_signal = Signal([float], [int], [str], [np.ndarray], [bool], [QVariant], [list])

    def __init__(self, channel: channel.PyDMChannel, address: str, protocol: str = None, parent: QObject = None, *args, **kwargs):
        super().__init__(channel=channel,
                         address=address,
                         protocol=protocol,
                         parent=parent,
                         *args,
                         **kwargs)
        logging.basicConfig()
        self.log: logging.Logger = logging.getLogger(__package__)
        self.log.setLevel(logging.DEBUG)

        self._device_prop = self.address[1:] if self.address.startswith('/') else self.address

        self._selector = None
        self._japc_additional_args = {}
        parsed_addr = split_device_property(self._device_prop)
        if parsed_addr.selector:
            self._device_prop = parsed_addr.address
            self._japc_additional_args['timingSelectorOverride'] = self._selector = parsed_addr.selector

        self.add_listener(channel)

    def add_listener(self, channel: channel.PyDMChannel):
        is_first_connection: bool = self.listener_count == 0

        # Superclass does not implement signal for bool values
        if channel.value_slot is not None:
            try:
                self.new_value_signal[bool].connect(channel.value_slot, Qt.QueuedConnection)
            except TypeError:
                pass
            try:
                self.new_value_signal[list].connect(channel.value_slot, Qt.QueuedConnection)
            except TypeError:
                pass
            try:
                self.new_value_signal[QVariant].connect(channel.value_slot, Qt.QueuedConnection)
            except TypeError:
                pass

        super().add_listener(channel)

        if channel.value_signal is not None:
            self.log.info(f'Adding write callback for {self.address}')
            self._connect_write_slots(channel.value_signal)

        if is_first_connection:
            self.connected = self._connect_to_japc()
            self._send_connection_state(self.connected)
            if self.connected:
                self.log.info(f'{self.protocol}://{self.address} connected!')
        else:
            # Artificially emit a single value to allow the UI update once because subscription
            # is not initiated here, thus we are not getting initial values
            get_japc().getParam(parameterName=self._device_prop, onValueReceived=self._on_async_get, **self._japc_additional_args)

        if is_read_only():
            self.write_access_signal.emit(False)
        else:
            # Allow write to all widgets by default. Write permissions are defined in CCDB,
            # which pyjapc does not have access to, so we can't know if a property is writable at the moment
            self.write_access_signal.emit(True)

    def remove_listener(self, channel: channel.PyDMChannel, destroying=False):
        # Superclass does not implement signal for bool values
        if not destroying:
            self.log.info(f'Removing one of the listeners for {self.protocol}://{self.address}')
            if channel.value_slot is not None:
                try:
                    self.new_value_signal[bool].disconnect(channel.value_slot)
                except TypeError:
                    pass
                try:
                    self.new_value_signal[QVariant].disconnect(channel.value_slot)
                except TypeError:
                    pass
                try:
                    self.new_value_signal[list].disconnect(channel.value_slot)
                except TypeError:
                    pass
            if channel.value_signal is not None:
                channel.value_signal.disconnect(self._on_value_updated)
        else:
            self.log.info(f'Removing a listener for {self.protocol}://{self.address} and destroying channel connection')
        super().remove_listener(channel=channel, destroying=destroying)

    def close(self):
        if self.connected:
            self.log.info(f'Stopping JAPC subscriptions for {self.address}')
            get_japc().stopSubscriptions(parameterName=self._device_prop,
                                         selector=self._selector)
        super().close()

    def _on_async_get(self, initial_value: Any):
        self._send_connection_state(self.connected)
        self._on_value_received(parameterName=self._device_prop, value=initial_value)
        self.log.info(f'Added one more listener to {self.protocol}://{self.address}')

    def _connect_write_slots(self, signal: Signal):
        try:
            signal[str].connect(slot=self._on_value_updated, type=Qt.QueuedConnection)
        except TypeError:
            pass
        try:
            signal[bool].connect(slot=self._on_value_updated, type=Qt.QueuedConnection)
        except TypeError:
            pass
        try:
            signal[int].connect(slot=self._on_value_updated, type=Qt.QueuedConnection)
        except TypeError:
            pass
        try:
            signal[float].connect(slot=self._on_value_updated, type=Qt.QueuedConnection)
        except TypeError:
            pass
        try:
            signal[np.ndarray].connect(slot=self._on_value_updated, type=Qt.QueuedConnection)
        except TypeError:
            pass

    def _on_value_received(self, parameterName: str, value: Any, headerInfo=None):
        del parameterName, headerInfo # Unused argument (https://google.github.io/styleguide/pyguide.html#214-decision)

        try:
            self.new_value_signal[type(value)].emit(value)
        except KeyError:
            self.log.warning(f'Cannot propagate JAPC value ({type(value)}) to the widget. '
                             f'Signal override is not defined.')

    def _on_value_updated(self, new_val: Any):
        get_japc().setParam(parameterName=self._device_prop,
                            parameterValue=new_val,
                            **self._japc_additional_args)

    def _send_connection_state(self, connected: bool):
        self.connection_state_signal.emit(connected)

    def _connect_to_japc(self) -> bool:
        japc = get_japc()

        try:
            japc.try_rbac_login()
        except BaseException as e:
            self.log.error(f'RBAC login failed. Check your permissions. Underlying error: {str(e)}')
            return False

        try:
            japc.subscribeParam(parameterName=self._device_prop,
                                onValueReceived=self._on_value_received,
                                **self._japc_additional_args)
            japc.startSubscriptions(parameterName=self._device_prop,
                                    selector=self._selector)
        except Exception as e:
            self.log.error(f'Unexpected error while subscribing to {self.address}'
                           '. Please verify the parameters and make sure the address is in the form'
                           f'\'{self.protocol}://device/property#field@selector\' or'
                           f'\'{self.protocol}://device/prop#field\' or'
                           f'\'{self.protocol}://device/property\'. Underlying problem: {str(e)}')
            return False

        return True


class JapcPlugin(plugin.PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "japc://" scheme.
    """

    protocol = 'japc'
    connection_class = _JapcConnection


class Rda3Plugin(plugin.PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rda3://" scheme.
    """

    protocol = 'rda3'
    connection_class = _JapcConnection


class Rda2Plugin(plugin.PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rda://" scheme.
    """

    protocol = 'rda'
    connection_class = _JapcConnection


class TgmPlugin(plugin.PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "tgm://" scheme.
    """

    protocol = 'tgm'
    connection_class = _JapcConnection


class NoPlugin(plugin.PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "no://" scheme.
    """

    protocol = 'no'
    connection_class = _JapcConnection


_DevicePropertySplitModel = namedtuple('_DevicePropertySplitModel', 'address selector')


def split_device_property(address: str) -> _DevicePropertySplitModel:
    """
    Separates device/property/field bunch from the timing user selector.

    Produces a named tuple with corresponding fields.

    Args:
        address: Original address string

    Returns:
        Named tuple with "address" and "selector" fields.
    """
    try:
        addr, sel = address.split('@')
    except ValueError:
        return _DevicePropertySplitModel(address=address, selector=None)
    return _DevicePropertySplitModel(address=addr, selector=sel)