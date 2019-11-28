import logging
import pyjapc
import datetime
import numpy as np
import jpype
from pydm.data_plugins import is_read_only
from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from qtpy.QtCore import Qt, QObject, Slot, Signal, QVariant
from typing import Any, Optional, Union, cast, Callable
from collections import namedtuple
from comrad.qt.application import CApplication
from comrad.qt.rbac import RBACLoginStatus
from comrad.data.jpype import get_user_message


logger = logging.getLogger(__name__)


cern = jpype.JPackage('cern')


# Unfortunately, we cannot import
# from pydm.widgets import channel OR
# from pydm.widgets.channel import PyDMChannel
# because it crashes with error "unable to import is_qt_designer"
# We need this import purely for typings. Therefore, we make a local stub
class PyDMChannel:

    value_signal: Optional[Signal]
    value_slot: Optional[Slot]

    def connect(self):
        pass

    def disconnect(self, destroying=False):
        pass


class _JapcService(QObject, pyjapc.PyJapc):
    """Singleton instance to avoid RBAC login for multiple Japc connections."""

    japc_status_changed = Signal(bool)
    japc_login_error = Signal(str)

    def __init__(self,
                 selector: str,
                 incaAcceleratorName: str,
                 noSet: bool = False,
                 timeZone: Union[str, datetime.tzinfo] = 'utc',
                 logLevel: Optional[int] = None,
                 *args,
                 **kwargs):
        QObject.__init__(self)
        pyjapc.PyJapc.__init__(self,
                               selector=selector,
                               incaAcceleratorName=incaAcceleratorName,
                               noSet=noSet,
                               timeZone=timeZone,
                               logLevel=logLevel,
                               *args,
                               **kwargs)
        self._logged_in: bool = False
        self._app = cast(CApplication, CApplication.instance())
        self._app.rbac.rbac_logout_user.connect(self.rbacLogout)
        self._app.rbac.rbac_login_user.connect(self.login_by_credentials)
        self._app.rbac.rbac_login_by_location.connect(self.login_by_location)
        self.japc_login_error.connect(self._app.rbac.rbac_on_error)

    def login_by_location(self):
        self.rbacLogin(on_exception=self._login_err)
        if self._logged_in:
            self._app.rbac.user = self.rbacGetToken().getUser().getName()  # FIXME: This is Java call. We need to abstract it into PyRBAC
            self._app.rbac.status = RBACLoginStatus.LOGGED_IN_BY_LOCATION

    def login_by_credentials(self, username: str, password: str):
        self.rbacLogin(username=username, password=password, on_exception=self._login_err)
        if self._logged_in:
            self._app.rbac.user = self.rbacGetToken().getUser().getName()  # FIXME: This is Java call. We need to abstract it into PyRBAC
            self._app.rbac.status = RBACLoginStatus.LOGGED_IN_BY_CREDENTIALS

    @property
    def logged_in(self):
        return self._logged_in

    def rbacLogin(self,
                  username: Optional[str] = None,
                  password: Optional[str] = None,
                  loginDialog: bool = False,
                  readEnv: bool = True,
                  on_exception: Optional[Callable[[str], None]] = None,
                  ):
        if self._logged_in:
            return
        try:
            super().rbacLogin(username=username,
                              password=password,
                              loginDialog=loginDialog,
                              readEnv=readEnv)
            self._set_online(True)
        except jpype.JException(cern.rbac.client.authentication.AuthenticationException) as e:
            if on_exception is not None:
                message = get_user_message(e)
                on_exception(message)
            self._set_online(False)

    def rbacLogout(self):
        if self._logged_in:
            super().rbacLogout()
            self._set_online(False)

    def setParam(self, *args, **kwargs):
        if not self._logged_in:
            logger.warning('Cannot set param because RBAC was not passed previously')
        else:
            super().setParam(*args, **kwargs)

    def stopSubscriptions(self, parameterName: Optional[str] = None, selector: Optional[str] = None):
        super().stopSubscriptions(parameterName=parameterName, selector=selector)
        if not self._subscriptionHandleDict:
            logger.info(f'Last subscription was removed from JAPC. Logging out.')
            self.rbacLogout()

    def _set_online(self, logged_in: bool):
        self._logged_in = logged_in
        self.japc_status_changed.emit(logged_in)
        if not logged_in:
            self._app.rbac.status = RBACLoginStatus.LOGGED_OUT

    def _login_err(self, message: str):
        self.japc_login_error.emit(message)


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


class _JapcConnection(PyDMConnection):
    """ PyDM adaptation for JAPC protocol. """

    # Superclass does not implement signal for bool values
    new_value_signal = Signal([float], [int], [str], [np.ndarray], [bool], [QVariant], [list])

    def __init__(self, channel: PyDMChannel, address: str, protocol: Optional[str] = None, parent: Optional[QObject] = None, *args, **kwargs):
        super().__init__(channel=channel,
                         address=address,
                         protocol=protocol,
                         parent=parent,
                         *args,
                         **kwargs)
        self._device_prop = self.address[1:] if self.address.startswith('/') else self.address

        self._selector: Optional[str] = None
        self._japc_additional_args = {}
        get_japc().japc_status_changed.connect(self._on_japc_status_changed)
        parsed_addr = split_device_property(self._device_prop)
        if parsed_addr.selector:
            self._device_prop = parsed_addr.address
            self._japc_additional_args['timingSelectorOverride'] = self._selector = parsed_addr.selector

        self.add_listener(channel)

    def add_listener(self, channel: PyDMChannel):
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

        # Allow write to all widgets by default. Write permissions are defined in CCDB,
        # which pyjapc does not have access to, so we can't know if a property is writable at the moment
        # TODO: This should be considering CCDA
        self.write_access_signal.emit(not is_read_only())

        if channel.value_signal is not None:
            logger.info(f'Adding write callback for {self.address}')
            self._connect_write_slots(channel.value_signal)

        connected: bool
        japc = get_japc()
        if is_first_connection and not japc.logged_in:
            try:
                japc.login_by_location()
            except BaseException:
                logger.info('Login by location failed. User will have to manually acquire RBAC token.')
        else:
            # Not callback will be received because login is not attempted
            # So we need to attach subscriptions manually
            self._on_japc_status_changed(connected=japc.logged_in)

    def remove_listener(self, channel: PyDMChannel, destroying: bool = False):
        # Superclass does not implement signal for bool values
        if not destroying:
            logger.info(f'Removing one of the listeners for {self.protocol}://{self.address}')
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
            logger.info(f'Removing a listener for {self.protocol}://{self.address} and destroying channel connection')
        super().remove_listener(channel=channel, destroying=destroying)

    def close(self):
        if self.connected:
            logger.info(f'Stopping JAPC subscriptions for {self.address}')
            get_japc().stopSubscriptions(parameterName=self._device_prop,
                                         selector=self._selector)
        super().close()

    def _on_async_get(self, initial_value: Any):
        self._send_connection_state(self.connected)
        self._on_value_received(parameterName=self._device_prop, value=initial_value)
        logger.info(f'Added one more listener to {self.protocol}://{self.address}')

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
        del parameterName, headerInfo  # Unused argument (https://google.github.io/styleguide/pyguide.html#214-decision)

        try:
            self.new_value_signal[type(value)].emit(value)
        except KeyError:
            logger.warning(f'Cannot propagate JAPC value ({type(value)}) to the widget. '
                             f'Signal override is not defined.')

    def _on_value_updated(self, new_val: Any):
        get_japc().setParam(parameterName=self._device_prop,
                            parameterValue=new_val,
                            **self._japc_additional_args)

    def _send_connection_state(self, connected: bool):
        self.connected = connected
        self.connection_state_signal.emit(connected)

    def _create_subscription(self, is_new: bool) -> bool:
        japc = get_japc()
        if is_new:
            try:
                japc.subscribeParam(parameterName=self._device_prop,
                                    onValueReceived=self._on_value_received,
                                    **self._japc_additional_args)
                japc.startSubscriptions(parameterName=self._device_prop,
                                        selector=self._selector)
            except Exception as e:
                logger.error(f'Unexpected error while subscribing to {self.address}'
                               '. Please verify the parameters and make sure the address is in the form'
                               f"'{self.protocol}://device/property#field@selector' or"
                               f"'{self.protocol}://device/prop#field' or"
                               f"'{self.protocol}://device/property'. Underlying problem: {str(e)}")
                return False
        else:
            # Artificially emit a single value to allow the UI update once because subscription
            # is not initiated here, thus we are not getting initial values
            japc.getParam(parameterName=self._device_prop,
                          onValueReceived=self._on_async_get,
                          **self._japc_additional_args)
        return True

    def _on_japc_status_changed(self, connected: bool):
        is_first_connection = self.listener_count == 1
        prev_connected = self.connected
        if not prev_connected and connected:
            connected = self._create_subscription(is_new=is_first_connection)
            self._send_connection_state(connected)


class JapcPlugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "japc://" scheme.
    """

    protocol = 'japc'
    connection_class = _JapcConnection


class Rda3Plugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rda3://" scheme.
    """

    protocol = 'rda3'
    connection_class = _JapcConnection


class Rda2Plugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rda://" scheme.
    """

    protocol = 'rda'
    connection_class = _JapcConnection


class TgmPlugin(PyDMPlugin):
    """
    PyDM data plugin that handles communications with the channels on "tgm://" scheme.
    """

    protocol = 'tgm'
    connection_class = _JapcConnection


class NoPlugin(PyDMPlugin):
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
