import logging
import pyjapc
import numpy as np
import jpype
from pydm.data_plugins import is_read_only
from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from qtpy.QtCore import Qt, QObject, Slot, Signal, QVariant
from typing import Any, Optional, cast, Callable
from collections import namedtuple
from comrad.rbac import RBACLoginStatus, RBACStartupLoginPolicy
from comrad.app.application import CApplication
from comrad.data.jpype import get_user_message


logger = logging.getLogger('comrad_japc')


cern = jpype.JPackage('cern')


# Unfortunately, we cannot import
# from pydm.widgets import channel OR
# from pydm.widgets.channel import PyDMChannel
# because it crashes with error "unable to import is_qt_designer"
# We need this import purely for typings. Therefore, we make a local stub
# TODO: This should be removed when corresponding issue is fixed
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
    japc_login_error = Signal(tuple)
    japc_param_error = Signal(str, bool)

    def __init__(self):
        app = cast(CApplication, CApplication.instance())
        if not app.use_inca:
            logger.debug(f'User has opted-out from using InCA')

        # This has to be set before super, as it will be accessed in JVM setup hook
        self._app = app

        # We don't need to call separate initializers here, because QObject will call PyJapc intializer by default.
        # It is also reflected in the examples of the PyQt5 documentation:
        # https://www.riverbankcomputing.com/static/Docs/PyQt5/multiinheritance.html

        # Selector is important to set, otherwise the default PyJapc selector tends to be LHC.USER.ALL
        # which fails to read data from private virtual devices.
        # When passing selector, it is important to set incaAcceleratorName, because default 'auto' name
        # will try to infer the accelerator from the selector and will fail, if we are passing None
        super().__init__(None,
                         selector='',
                         incaAcceleratorName='' if app.use_inca else None)
        self._logged_in: bool = False
        self._use_inca = app.use_inca
        self._app.rbac.rbac_logout_user.connect(self.rbacLogout)
        self._app.rbac.rbac_login_user.connect(self.login_by_credentials)
        self._app.rbac.rbac_login_by_location.connect(self.login_by_location)
        self.japc_login_error.connect(self._app.rbac.rbac_on_error)
        self.japc_param_error.connect(self._app.on_control_error)
        logger.debug(f'JAPC is set up and ready!')

        if app.rbac.startup_login_policy == RBACStartupLoginPolicy.LOGIN_BY_LOCATION:
            logger.debug(f'Attempting login by location on the first connection')
            try:
                self.login_by_location()
            except BaseException:
                logger.info('Login by location failed. User will have to manually acquire RBAC token.')
        elif app.rbac.startup_login_policy == RBACStartupLoginPolicy.LOGIN_BY_CREDENTIALS:
            # TODO: Implement presenting a dialog here
            pass

    def login_by_location(self):
        logger.debug(f'Attempting RBAC login by location')
        self.rbacLogin(on_exception=self._login_err)
        if self._logged_in:
            token = self.rbacGetToken()
            if token:
                self._app.rbac.user = token.getUser().getName()  # FIXME: This is Java call. We need to abstract it into PyRBAC
                self._app.rbac.status = RBACLoginStatus.LOGGED_IN_BY_LOCATION

    def login_by_credentials(self, username: str, password: str):
        logger.debug(f'Attempting RBAC login with credentials')
        self.rbacLogin(username=username, password=password, on_exception=self._login_err)
        if self._logged_in:
            token = self.rbacGetToken()
            if token:
                self._app.rbac.user = token.getUser().getName()  # FIXME: This is Java call. We need to abstract it into PyRBAC
                self._app.rbac.status = RBACLoginStatus.LOGGED_IN_BY_CREDENTIALS

    @property
    def logged_in(self):
        return self._logged_in

    def rbacLogin(self,
                  username: Optional[str] = None,
                  password: Optional[str] = None,
                  loginDialog: bool = False,
                  readEnv: bool = True,
                  on_exception: Optional[Callable[[str, bool], None]] = None,
                  ):
        if self._logged_in:
            return
        logger.debug(f'Performing RBAC login')
        try:
            super().rbacLogin(username=username,
                              password=password,
                              loginDialog=loginDialog,
                              readEnv=readEnv)
        except jpype.JException(cern.rbac.client.authentication.AuthenticationException) as e:
            if on_exception is not None:
                message = get_user_message(e)
                login_by_location = not username and not password
                on_exception(message, login_by_location)
            self._set_online(False)
            return
        self._set_online(True)

    def rbacLogout(self):
        if self._logged_in:
            super().rbacLogout()
            self._set_online(False)

    def getParam(self, *args, **kwargs):
        return self._expect_cmw_error(super().getParam, *args, **kwargs)

    def setParam(self, *args, **kwargs):
        if not self._use_inca and 'checkDims' not in kwargs:
            # Because when InCA is not set up, setter will crash because it will fail to
            # receive valueDescriptor while trying to verify dimensions.
            kwargs['checkDims'] = False
        self._expect_cmw_error(super().setParam, *args, display_popup=True, **kwargs)

    def _set_online(self, logged_in: bool):
        self._logged_in = logged_in
        self.japc_status_changed.emit(logged_in)
        if not logged_in:
            self._app.rbac.status = RBACLoginStatus.LOGGED_OUT

    def _login_err(self, message: str, login_by_location: bool):
        self.japc_login_error.emit((message, login_by_location))

    def _expect_cmw_error(self, fn: Callable, *args, display_popup: bool = False, **kwargs):
        try:
            return fn(*args, **kwargs)
        except jpype.JException(cern.japc.core.ParameterException) as e:
            message = get_user_message(e)
            self.japc_param_error.emit(message, display_popup)

    def _setup_jvm(self, log_level: int):
        """Overrides internal PyJapc hook to set any custom JVM flags"""
        super()._setup_jvm(log_level=log_level)
        for name, val in self._app.jvm_flags.items():
            logger.debug(f'Setting extra JVM flag: {name}={val}')
            jpype.java.lang.System.setProperty(name, str(val))


_japc: Optional[_JapcService] = None


def get_japc() -> _JapcService:
    """
    Method to retrieve a singleton of the JAPC service instance.

    It is done to avoid multiple log-in attempts when having several channels working with JAPC.

    Returns:
        Singleton instance.
    """

    global _japc
    if _japc is None:
        _japc = _JapcService()
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
        self._subscriptions_active: bool = False
        self._selector: Optional[str] = None
        self._japc_additional_args = {}
        self._some_subscriptions_failed: bool = False
        parsed_addr = split_device_property(self._device_prop)
        if parsed_addr.selector:
            self._device_prop = parsed_addr.address
            self._japc_additional_args['timingSelectorOverride'] = self._selector = parsed_addr.selector

        get_japc().japc_status_changed.connect(self._on_japc_status_changed)
        self.add_listener(channel)

    def add_listener(self, channel: PyDMChannel):
        logger.debug(f'Adding a listener for {self._device_prop}')
        super().add_listener(channel)
        self._connect_extra_signal_types(channel)

        if channel.value_signal is not None:
            logger.debug(f'Adding write callback for {self.protocol}://{self.address}')
            self._connect_write_slots(channel.value_signal)

        # Allow write to all widgets by default. Write permissions are defined in CCDB,
        # which pyjapc does not have access to, so we can't know if a property is writable at the moment
        # TODO: This should be considering CCDA
        enable_write_access = not is_read_only()
        logger.debug(f'Emitting write access for {self._device_prop}: {enable_write_access}')
        self.write_access_signal.emit(enable_write_access)

        # Issue a connection signal (e.g. if it's an additional listener for already connected channel, we need to let
        # it know that we are already connected
        self.connection_state_signal.emit(self.online)

        # Start receiving values
        if channel.value_slot is not None:
            self._create_subscription()
        else:
            # Value is never to be received (for instance on buttons that work with commands)
            # We still need to notify the system that we are "connected"
            self.online = True

    def remove_listener(self, channel: PyDMChannel, destroying: bool = False):
        # Superclass does not implement signal for bool values
        if not destroying:
            logger.debug(f'Removing one of the listeners for {self.protocol}://{self.address}')
            if channel.value_slot is not None:
                try:
                    self.new_value_signal[bool].disconnect(channel.value_slot)
                except (KeyError, TypeError):
                    pass
                try:
                    self.new_value_signal[QVariant].disconnect(channel.value_slot)
                except (KeyError, TypeError):
                    pass
                try:
                    self.new_value_signal[list].disconnect(channel.value_slot)
                except (KeyError, TypeError):
                    pass
            if channel.value_signal is not None:
                channel.value_signal.disconnect(self._on_set_device_property)
                try:
                    channel.value_signal[str].disconnect(self._on_set_device_property)
                except (KeyError, TypeError):
                    pass
                try:
                    channel.value_signal[bool].disconnect(self._on_set_device_property)
                except (KeyError, TypeError):
                    pass
                try:
                    channel.value_signal[int].disconnect(self._on_set_device_property)
                except (KeyError, TypeError):
                    pass
                try:
                    channel.value_signal[float].disconnect(self._on_set_device_property)
                except (KeyError, TypeError):
                    pass
                try:
                    channel.value_signal[np.ndarray].disconnect(self._on_set_device_property)
                except (KeyError, TypeError):
                    pass
        else:
            logger.debug(f'Removing a listener for {self.protocol}://{self.address} and destroying channel connection')
        super().remove_listener(channel=channel, destroying=destroying)

    def close(self):
        if self.online:
            logger.debug(f'Stopping JAPC subscriptions for {self.address}')
            self.online = False
            get_japc().stopSubscriptions(parameterName=self._device_prop,
                                         selector=self._selector)
        super().close()

    def _on_async_get(self, initial_value: Any):
        logger.debug(f'Received async GET callback on {self.protocol}://{self.address}')
        self._on_get_device_property(parameterName=self._device_prop, value=initial_value)
        logger.debug(f'Added one more listener to {self.protocol}://{self.address}')

    def _connect_extra_signal_types(self, channel: PyDMChannel):
        # Superclass does not implement signal for bool values
        if channel.value_slot is not None:
            try:
                self.new_value_signal[bool].connect(channel.value_slot, Qt.QueuedConnection)
            except (KeyError, TypeError):
                pass
            try:
                self.new_value_signal[list].connect(channel.value_slot, Qt.QueuedConnection)
            except (KeyError, TypeError):
                pass
            try:
                self.new_value_signal[QVariant].connect(channel.value_slot, Qt.QueuedConnection)
            except (KeyError, TypeError):
                pass

    def _connect_write_slots(self, signal: Signal):
        set_slot_connected: bool = False
        try:
            signal[str].connect(slot=self._on_set_device_property, type=Qt.QueuedConnection)
            set_slot_connected = True
        except (KeyError, TypeError):
            pass
        try:
            signal[bool].connect(slot=self._on_set_device_property, type=Qt.QueuedConnection)
            set_slot_connected = True
        except (KeyError, TypeError):
            pass
        try:
            signal[int].connect(slot=self._on_set_device_property, type=Qt.QueuedConnection)
            set_slot_connected = True
        except (KeyError, TypeError):
            pass
        try:
            signal[float].connect(slot=self._on_set_device_property, type=Qt.QueuedConnection)
            set_slot_connected = True
        except (KeyError, TypeError):
            pass
        try:
            signal[np.ndarray].connect(slot=self._on_set_device_property, type=Qt.QueuedConnection)
            set_slot_connected = True
        except (KeyError, TypeError):
            pass

        if not set_slot_connected:
            try:
                signal.connect(slot=self._on_device_command, type=Qt.QueuedConnection)
            except (KeyError, TypeError):
                pass

    def _on_get_device_property(self, parameterName: str, value: Any, headerInfo=None):
        del parameterName, headerInfo  # Unused argument (https://google.github.io/styleguide/pyguide.html#214-decision)

        self.online = True

        try:
            self.new_value_signal[type(value)].emit(value)
        except KeyError:
            logger.warning(f'Cannot propagate JAPC value ({type(value)}) to the widget. '
                           'Signal override is not defined.')

    @Slot()
    def _on_device_command(self):
        get_japc().setParam(parameterName=self._device_prop,
                            parameterValue={},
                            **self._japc_additional_args)

    @Slot(str)
    @Slot(bool)
    @Slot(int)
    @Slot(float)
    @Slot(np.ndarray)
    def _on_set_device_property(self, new_val: Any):
        get_japc().setParam(parameterName=self._device_prop,
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
            logger.debug(f'Channel {self.protocol}://{self.address} is {"online" if connected else "offline"}')
            self.connection_state_signal.emit(connected)

    def _create_subscription(self) -> bool:
        japc = get_japc()
        if not self.online:
            logger.debug(f'Subscribing to JAPC at {self._device_prop}')
            japc.subscribeParam(parameterName=self._device_prop,
                                onValueReceived=self._on_get_device_property,
                                onException=self._on_subscription_exception,
                                **self._japc_additional_args)
            self._start_subscriptions()
        else:
            logger.debug(f'Initiating a single GET to {self._device_prop} to update the displayed value')
            # Artificially emit a single value to allow the UI update once because subscription
            # is not initiated here, thus we are not getting initial values
            japc.getParam(parameterName=self._device_prop,
                          onValueReceived=self._on_async_get,
                          **self._japc_additional_args)

    def _start_subscriptions(self):
        logger.debug(f'Starting subscriptions')
        try:
            get_japc().startSubscriptions(parameterName=self._device_prop, selector=self._selector)
        except Exception as e:
            # TODO: Catch more specific Jpype errors here
            logger.exception(f'Unexpected error while subscribing to {self.address}'
                             '. Please verify the parameters and make sure the address is in the form'
                             f"'{self.protocol}:///device/property#field@selector' or"
                             f"'{self.protocol}:///device/prop#field' or"
                             f"'{self.protocol}:///device/property'. Underlying problem: {str(e)}")

    def _on_subscription_exception(self, param_name: str, description: str, exception: Exception):
        logger.exception(f'Exception {type(exception).__name__} triggered on {param_name}: {exception.getMessage()}')
        self._some_subscriptions_failed = True

    def _on_japc_status_changed(self, logged_in: bool):
        if logged_in and (not self.online or self._some_subscriptions_failed):
            logger.debug(f'Reviving blocked subscriptions after login')
            self._some_subscriptions_failed = False
            # Need to stop subscriptions before restarting, otherwise they will not start
            get_japc().stopSubscriptions(parameterName=self._device_prop, selector=self._selector)
            self._start_subscriptions()


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
