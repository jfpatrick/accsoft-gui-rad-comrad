import logging
from qtpy.QtCore import QObject
from typing import Any, Optional, Callable, Dict
from comrad.data.addr import ControlEndpointAddress
from comrad.data.pyjapc_patch import CPyJapc
from comrad.data_plugins import CCommonDataConnection, CDataPlugin, CChannelData, CChannel


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


class CJapcConnection(CCommonDataConnection):

    def __init__(self, channel: CChannel, address: str, protocol: Optional[str] = None, parent: Optional[QObject] = None):
        """
        Connection serves one or multiple listeners that communicate with JAPC protocol by directing the calls into
        :mod:`PyJapc API <pyjapc>`.

        Args:
            channel: Initial channel to connect to the :class:`~pyjapc.PyJapc`.
            address: Address string of the device to be connected to.
            protocol: Protocol representation. Should be ``japc://``.
            parent: Optional parent owner.
            *args: Any additional arguments needed by :class:`~pydm.data_plugins.plugin.PyDMConnection`.
            **kwargs: Any additional keyword arguments needed by :class:`~pydm.data_plugins.plugin.PyDMConnection`
        """
        super().__init__(channel=channel,
                         address=address,
                         protocol=protocol,
                         parent=parent)

        self._meta_field: Optional[str] = None
        self._selector: Optional[str] = None
        self._japc_additional_args: Dict[str, Any] = {}
        self._some_subscriptions_failed: bool = False
        self._pyjapc_param_name: str = ''
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

        get_japc().japc_status_changed.connect(self._on_japc_status_changed)
        self.add_listener(channel)

    def add_listener(self, channel: CChannel):
        if not self._pyjapc_param_name:
            logger.error('Connection is not initialized. Will not add a listener.')
            return

        super().add_listener(channel)

    def read_only_for_listener(self, address: str) -> bool:
        # Allow write to all widgets by default. Write permissions are defined in CCDB,
        # which pyjapc does not have access to, so we can't know if a property is writable at the moment
        # TODO: This should be considering CCDA
        return super().read_only_for_listener(address)

    def send_command(self):
        self.set(value={})

    def get(self, callback: Callable[[str, Any, Dict[str, Any]], None]):
        get_japc().getParam(parameterName=self._pyjapc_param_name,
                            onValueReceived=callback,
                            getHeader=True,  # Needed for meta-fields
                            noPyConversion=False,
                            **self._japc_additional_args)

    def set(self, value: Any):
        get_japc().setParam(parameterName=self._pyjapc_param_name,
                            parameterValue=value,
                            **self._japc_additional_args)

    def subscribe(self, callback: Callable[[str, Any, Dict[str, Any]], None]):
        logger.debug(f'{self}: Subscribing to JAPC')
        get_japc().subscribeParam(parameterName=self._pyjapc_param_name,
                                  onValueReceived=callback,
                                  onException=self._on_subscription_exception,
                                  getHeader=True,  # Needed for meta-fields
                                  noPyConversion=False,
                                  **self._japc_additional_args)
        self._start_subscriptions()

    def unsubscribe(self):
        get_japc().clearSubscriptions(parameterName=self._pyjapc_param_name,
                                      selector=self._selector)

    def process_incoming_value(self, parameterName: str, value: Any, headerInfo: Dict[str, Any]) -> CChannelData[Any]:  # type: ignore  # arguments are different from super
        # These parameters are defined to the signature, expected by PyJapc
        _ = parameterName

        if self._meta_field is not None:
            # We are looking inside header instead of the value, because user has requested
            # data from a "special" field, which is a meta-field that is placed in header on the transport level
            reply_key = SPECIAL_FIELDS[self._meta_field]
            try:
                value = headerInfo[reply_key]
            except KeyError:
                raise ValueError(f'Cannot locate meta-field "{self._meta_field}" inside packet header ({headerInfo}).')
        elif self._is_property_level and isinstance(value, dict):
            # To not put logic of resolving "special" fields into widgets that work with the whole property,
            # we populate meta fields into the property, like if it was data
            for request_key, reply_key in SPECIAL_FIELDS.items():
                try:
                    meta_val = headerInfo[reply_key]
                except KeyError:
                    continue
                value[request_key] = meta_val

        return CChannelData[Any](value=value, meta_info=headerInfo)

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
        if logged_in and (not self.connected or self._some_subscriptions_failed):
            logger.debug(f'{self}: Reviving blocked subscriptions after login')
            self._some_subscriptions_failed = False
            # Need to stop subscriptions before restarting, otherwise they will not start
            get_japc().stopSubscriptions(parameterName=self._pyjapc_param_name, selector=self._selector)
            self._start_subscriptions()


class JapcPlugin(CDataPlugin):
    """
    PyDM data plugin that handles communications with the channels on "japc://" scheme.
    """

    protocol = 'japc'
    connection_class = CJapcConnection


class Rda3Plugin(CDataPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rda3://" scheme.
    """

    protocol = 'rda3'
    connection_class = CJapcConnection


class Rda2Plugin(CDataPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rda://" scheme.
    """

    protocol = 'rda'
    connection_class = CJapcConnection


class TgmPlugin(CDataPlugin):
    """
    PyDM data plugin that handles communications with the channels on "tgm://" scheme.
    """

    protocol = 'tgm'
    connection_class = CJapcConnection


class NoPlugin(CDataPlugin):
    """
    PyDM data plugin that handles communications with the channels on "no://" scheme.
    """

    protocol = 'no'
    connection_class = CJapcConnection


class RmiPlugin(CDataPlugin):
    """
    PyDM data plugin that handles communications with the channels on "rmi://" scheme.
    """

    protocol = 'rmi'
    connection_class = CJapcConnection
