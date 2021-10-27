"""
This module subclasses PyJapc to fix numerous problems with its insufficient behavior so that
it can be used with ComRAD.
"""
import jpype
import logging
from enum import IntFlag, IntEnum
from typing import cast, Optional, Callable, Any, Dict, List, Union
from qtpy.QtCore import QObject, Signal
from pyjapc import PyJapc
from pyrbac import Token
from comrad.app.application import CApplication
from comrad.data.jpype_utils import get_cmw_user_message, get_java_user_message, meaning_from_jpype
from comrad.data.japc_enum import CEnumValue


logger = logging.getLogger('comrad.japc')


cern = jpype.JPackage('cern')


def _original_fixed_get_param(self,
                              parameterName,
                              getHeader=False,
                              noPyConversion=False,
                              unixtime=False,
                              onValueReceived=None,
                              onException=None,
                              **kwargs):
    """
    Copy of original PyJapc.getParam that has been patched to fix the faulty behavior and rejected a merge to
    pyjapc package. This should be used with care, because while it replicates the internal logic of PyJapc,
    it is drastically different from internal logic of PAPC. Thus, when PAPC is injected, this method should
    never be called.
    """
    try:
        from pyjapc._japc import _INSTANCE_DEFAULT
    except ImportError:
        logger.debug('PyJapc protected variable import issue. This might result in unexpected behavior')
        _INSTANCE_DEFAULT = None

    kwargs['timingSelectorOverride'] = kwargs.get('timingSelectorOverride', _INSTANCE_DEFAULT)
    kwargs['dataFilterOverride'] = kwargs.get('dataFilterOverride', _INSTANCE_DEFAULT)
    s = self._giveMeSelector(**kwargs)

    # Get the (cached) JAPC Parameter or ParameterGroup object
    p = self._getJapcPar(parameterName)

    # Carry out the Get operation. tempParValue will be of type:
    #  jpype._jclass.cern.japc.value.spi.AcquiredParameterValueImpl
    # or if a GET on a ParameterGroup was done:
    #  jpype._jarray.cern.japc.value.FailSafeParameterValue[]
    if onValueReceived is None:
        temp_val = p.getValue(s)
        return self._processTempValue(temp_value=temp_val, getHeader=getHeader, noPyConversion=noPyConversion,
                                      unixtime=unixtime)
    else:
        def onValueReceivedWrapper(parameterName, value, headerInfo=None):
            if getHeader:
                onValueReceived(parameterName, value, headerInfo)
            else:
                onValueReceived(parameterName, value)

        listener = self._createValueListener(par=p,
                                             getHeader=getHeader,
                                             noPyConversion=noPyConversion,
                                             unixtime=unixtime,
                                             onValueReceived=onValueReceivedWrapper,
                                             onException=onException)
        p.getValue(s, listener)


def _papc_extract_val(orig: Dict[str, Any]) -> Any:

    def enum_item_to_obj(enum_item: IntEnum) -> CEnumValue:
        code = enum_item.value
        label = enum_item.name
        return CEnumValue(code=code, label=label, meaning=CEnumValue.Meaning.NONE, settable=True)

    def flags_item_to_obj(flag_item: IntFlag) -> List[CEnumValue]:
        res = []
        for bit in type(flag_item):
            if bit in flag_item:
                res.append(CEnumValue(code=bit.value, label=bit.name, meaning=CEnumValue.Meaning.NONE, settable=False))
        return res

    val = orig['value']
    if isinstance(val, IntEnum):
        return enum_item_to_obj(val)
    elif isinstance(val, IntFlag):
        return flags_item_to_obj(val)
    else:
        return val


def _fixed_papc_get_param(self, parameterName, getHeader=False, noPyConversion=False,
                          unixtime=False, onValueReceived=None, onException=None, **kwargs):
    # The main difference here is that papc never passes the header to onValueReceived event
    # when getHeader is set to True. In addition, it runs custom logic to resolve enums and enum sets, similar to
    # how it overrides real PyJapc to convert into CEnumValue. Lastly, it removes useless papc warnings about not
    # implemented interfaces.
    # The rest is almost identical to v0.4 (except for fixing code style to keep linters happy)

    # We mimic the (ugly) interface exposed by PyJapc to support timingSelectorOverride.
    selector = kwargs.pop('timingSelectorOverride', self.selector)
    # if kwargs:
    #     self._raise_error(NotImplementedError('getParam with arbitrary kwargs not supported in simulation mode'))
    # if unixtime or noPyConversion:
    #     self._raise_error(NotImplementedError('unixtime and/or noPyConversion not supported in simulation mode'))
    # if onException:
    #     self._raise_error(NotImplementedError('onException not supported in simulation mode'))

    # TODO: we are not mimicking the exceptions raised just yet.
    from papc.reference import PropertyReference
    from papc.reference import FieldReference

    # Py36 workaround :(
    from papc.system import _parameter_ref_from_string, ParameterReferenceType
    PR_from_string = getattr(ParameterReferenceType, 'from_string', _parameter_ref_from_string)

    param_ref = PR_from_string(parameterName)
    result = self.system.get(param_ref, selector)

    # We have different behaviour for properties vs fields (for getHeader).
    # For props: we have a dictionary of ``{prop_name: values}, {prop_headers}``
    # For fields: we have ``value, {prop_headers}``
    if isinstance(param_ref, PropertyReference):
        # Pull out just the field name.
        f_name = lambda name: FieldReference(name).field
        value = {f_name(field): _papc_extract_val(data) for field, data in result.items()}
    else:
        # Get the only item out of the result dictionary.
        [field_result] = result.values()
        value = _papc_extract_val(field_result)

    if onValueReceived:
        if getHeader:
            header = self._get_header_base(selector)
            onValueReceived(parameterName, value, header)
        else:
            onValueReceived(value)
    else:
        if getHeader:
            header = self._get_header_base(selector)
            return value, header
        else:
            return value


def _fixed_papc_subscribe_param(self, parameterName, onValueReceived=None, onException=None, getHeader=False,
                                noPyConversion=False, unixtime=False, **kwargs):
    # The main difference here is that it runs custom logic to resolve enums and enum sets, similar to
    # how it overrides real PyJapc to convert into CEnumValue. Lastly, it removes useless papc warnings about not
    # implemented interfaces.
    # The rest is almost identical to v0.4 (except for fixing code style to keep linters happy)
    selector = kwargs.pop('timingSelectorOverride', self.selector)

    # if kwargs:
    #     self._raise_error(NotImplementedError('getParam with arbitrary kwargs not supported in simulation mode'))
    # if noPyConversion:
    #     self._raise_error(NotImplementedError('noPyConversion not supported in simulation mode'))
    # if unixtime:
    #     self._raise_error(NotImplementedError('unixtime not supported in simulation mode'))
    # if onException:
    #     self._raise_error(NotImplementedError('onException not supported in simulation mode'))

    from papc.reference import PropertyReference
    from papc.reference import FieldReference

    # Py36 workaround :(
    from papc.system import _parameter_ref_from_string, ParameterReferenceType
    PR_from_string = getattr(ParameterReferenceType, 'from_string', _parameter_ref_from_string)

    param_ref = PR_from_string(parameterName)

    # Track whether a result has been received yet for this subscription.
    first_result_received = False

    from papc.interfaces.pyjapc import JapcSubscription

    def prepare_result(result):
        nonlocal first_result_received
        toggled_header = []
        if getHeader:
            header = self._get_header_base(selector)
            header.update({'isFirstUpdate': not first_result_received})
            toggled_header.append(header)
        # Now that we have received at least one result,
        # we have been initialised.
        first_result_received = True
        if isinstance(param_ref, PropertyReference):
            # Pull out just the field name.
            p_name = str(param_ref)
            f_name = lambda name: FieldReference(name).field
            result = {f_name(field): _papc_extract_val(data) for field, data in result.items()}
            # args: property_name, values, headerInfos

            return onValueReceived(p_name, result, *toggled_header)
        else:
            name, info = result.popitem()
            # args: parameterName, value, headerInfo
            return onValueReceived(name, _papc_extract_val(info), *toggled_header)

    sub = self.system.subscriptions.create(parameterName, selector, prepare_result)
    sub = JapcSubscription(self.system, sub)

    self._subscriptions.append(sub)
    return sub


in_papc_mode = PyJapc.__module__.startswith('papc.')


if in_papc_mode:
    # Monkey-patch papc subscriptions with some expectations that TimingBar has about underlying Java objects
    from papc.interfaces.pyjapc import JapcSubscription
    from comrad.monkey import MonkeyPatchedClass, modify_in_place

    @modify_in_place
    class CPapcSubscription(JapcSubscription, MonkeyPatchedClass):

        def stopMonitoring(self, *args, **kwargs):
            # At the time of implementation, papc did not have this method. But just in case it was implemented
            # in the meantime, try calling the implementation.
            try:
                fn = self._overridden_members['stopMonitoring']
            except KeyError:
                return
            fn(self, *args, **kwargs)

    @modify_in_place
    class CPapc(PyJapc, MonkeyPatchedClass):

        def _transformSubscribeCacheKey(self, param_name: str, selector: Optional[str] = None) -> str:
            # At the time of implementation, papc did not have this method. But just in case it was implemented
            # in the meantime, try calling the implementation.
            try:
                fn = self._overridden_members['_transformSubscribeCacheKey']
            except KeyError:
                return f'{param_name}@{selector!s}'
            return fn(self, param_name, selector)

        @property
        def _subscriptionHandleDict(self):
            raise ValueError


class PyJapcWrapper(PyJapc):
    """
    This class wraps PyJapc with substituted methods, to localize method swizzling, to avoid influencing other
    PyJapc instances (not participating in PyDM data plugin system) that can
    be used in the user-code or other parts of the components, e.g. PyJapc used by TimingBarModel.

    This layer provides hacks that fix limiting behaviors of pyjapc and papc libraries.
    """

    # Papc has to have the same interface as PyJapc,
    # And we are fixing PyJapc interface, papc change needs to be done, but it cant
    # be submitted to the official papc, until official PyJapc is done. Until recently,
    # solution was to use forked papc, but it's not friendly for comrad release, as
    # might fail to download on machines that do not have ssh keys for gitlab, or if
    # we switched to https, would require users to always enter credentials.
    # The original forked fix is here: git+ssh://git@gitlab.cern.ch:7999/isinkare/papc.git@fix/async-get-interface
    getParam = _fixed_papc_get_param if in_papc_mode else _original_fixed_get_param

    # This replacement harmonizes processing of enums between getParam, subscribeParam to make it
    # similar to PyJapc's overridden _convertSimpleValToPy.
    subscribeParam = _fixed_papc_subscribe_param if in_papc_mode else PyJapc.subscribeParam


class CPyJapc(PyJapcWrapper, QObject):

    japc_status_changed = Signal(bool)
    japc_param_error = Signal(str, bool)

    @classmethod
    def instance(cls):
        """
        Method to retrieve a singleton of the JAPC service instance.

        It is done to avoid multiple log-in attempts when having several channels working with JAPC.
        Currently PyJapc also defeats the opportunity to use different instances with different InCA configuration
        setting. Therefore, we use singleton everywhere in for now.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Singleton instance to avoid RBAC login for multiple Japc connections."""
        app = cast(CApplication, CApplication.instance())
        if not app.use_inca:
            logger.debug('User has opted-out from using InCA')

        # This has to be set before super, as it will be accessed in JVM setup hook
        self._app = app

        # We don't need to call separate initializers here, because QObject will call PyJapc initializer by default.
        # It is also reflected in the examples of the PyQt5 documentation:
        # https://www.riverbankcomputing.com/static/Docs/PyQt5/multiinheritance.html

        # Selector is important to set, otherwise the default PyJapc selector tends to be LHC.USER.ALL
        # which fails to read data from private virtual devices.
        # When passing selector, it is important to set incaAcceleratorName, because default 'auto' name
        # will try to infer the accelerator from the selector and will fail, if we are passing None
        effective_level = logger.getEffectiveLevel()
        if effective_level == logging.INFO:
            # INFO output from Java libs is too chatty. Either leave that for DEBUG, or when warning or more critical
            # is specified (even though by default PyJapc will place WARN logging level internally anyway)
            effective_level = None
        PyJapcWrapper.__init__(self,
                               selector='',
                               incaAcceleratorName='' if app.use_inca else None,
                               logLevel=effective_level)
        QObject.__init__(self)
        self._logged_in: bool = False
        self._use_inca = app.use_inca
        self._app.rbac.logout_finished.connect(self.rbacLogout)
        self._app.rbac.login_succeeded.connect(self._inject_token)
        self.japc_param_error.connect(self._app.on_control_error)
        logger.debug('JAPC is set up and ready!')

        if self._app.rbac.token is not None:
            self._inject_token(self._app.rbac.token.get_encoded())

    def rbacLogout(self):
        if self._logged_in:
            super().rbacLogout()
            self._set_online(False)

    def getParam(self, *args, **kwargs):
        return self._expect_japc_error(super().getParam, *args, **kwargs)

    def setParam(self, *args, **kwargs):
        if not self._use_inca and 'checkDims' not in kwargs:
            # Because when InCA is not set up, setter will crash because it will fail to
            # receive valueDescriptor while trying to verify dimensions.
            kwargs['checkDims'] = False
        self._expect_japc_error(super().setParam, *args, display_popup=True, **kwargs)

    def _inject_token(self, pyrbac_token: Union[Token, bytes]):
        logger.debug('Updating Java-RBAC token with the external token from pyrbac')
        buffer: bytes = pyrbac_token.get_encoded() if isinstance(pyrbac_token, Token) else pyrbac_token
        try:
            java: Any = jpype.java  # type: ignore  # mypy fails all imports from jpype package in Python 3.9
            new_token = cern.rbac.common.RbaToken.parseAndValidate(java.nio.ByteBuffer.wrap(buffer))
        except Exception as e:  # noqa: B902
            # Can fail, e.g. with error
            # cern.rbac.common.TokenFormatException:
            # Token's signature is invalid - only tokens issued by the RBAC <RBAC_ENV> Server are accepted.
            logger.error(f'Java refused generated token: {e!s}')
        else:
            cern.rbac.util.holder.ClientTierTokenHolder.setRbaToken(new_token)
            self._set_online(logged_in=self.rbacGetToken() is not None)

    def _set_online(self, logged_in: bool):
        self._logged_in = logged_in
        self.japc_status_changed.emit(logged_in)

    def _expect_japc_error(self, fn: Callable, *args, display_popup: bool = False, **kwargs):
        try:
            return fn(*args, **kwargs)
        except jpype.JException as e:  # type: ignore  # mypy fails all imports from jpype package in Python 3.9
            # We can't catch concrete exceptions in the 'except' clause directly, because Python
            # interpreter will complain when used with PAPC, as cern package won't be loaded,
            # and the exception won't be found. In PAPC scenario, this except block should never be
            # executed, thus avoiding the error.
            if isinstance(e, (cern.japc.core.ParameterException,  # CMW error, e.g. SET not supported
                              cern.japc.value.ValueConversionException)):  # JAPC error, e.g. wrong enum value
                message = get_cmw_user_message(e)
            else:
                message = get_java_user_message(e)
        except ValueError as e:
            # Catch PyJapc-level errors, e.g.
            # "ValueError: Could not get a valueDescriptor. Can not do array dimension checks. Please initialize INCA in the PyJapc() constructor."
            message = str(e)
        else:
            return
        self.japc_param_error.emit(message, display_popup)

    def _setup_jvm(self, log_level: Union[int, str, None]):
        """Overrides internal PyJapc hook to set any custom JVM flags"""
        # This is a workaround for PyJapc not correctly converting Python log levels into log4j
        # TODO: This workaround can be removed when PyJapc is fixed and its version is bumped
        if log_level is not None and isinstance(log_level, int):
            log_level = logging.getLevelName(log_level)
            # Adapt to log4j names: https://logging.apache.org/log4j/2.x/manual/customloglevels.html
            if log_level == 'WARNING':
                log_level = 'WARN'
            elif log_level == 'NOTSET':
                log_level = 'OFF'

        super()._setup_jvm(log_level=log_level)
        for name, val in self._app.jvm_flags.items():
            logger.debug(f'Setting extra JVM flag: {name}={val}')
            jpype.java.lang.System.setProperty(name, str(val))  # type: ignore

        def print_token(token):
            token_info: str = 'None'
            if token:
                user = token.getUser()  # Java call
                if user:
                    token_info = user.getName()  # Java call
                else:
                    # Happens, e.g. in tests, when passing empty pyrbac token into Java
                    token_info = 'Unknown user'
            logger.debug(f'Java received new RBAC token: {token_info}')

        JProxy: Any = jpype.JProxy  # type: ignore  # mypy fails all imports from jpype package in Python 3.9
        listener = JProxy('cern.rbac.util.holder.ClientTierRbaTokenChangeListener', {
            'rbaTokenChanged': print_token,
        })
        cern.rbac.util.holder.ClientTierTokenHolder.addRbaTokenChangeListener(listener)

    def _convertSimpleValToPy(self, val) -> Any:
        """Overrides internal PyJapc method to emit different data struct for enums."""
        typename = val.getValueType().toString().lower()

        def enum_item_to_obj(enum_item: Any) -> CEnumValue:
            return CEnumValue(code=enum_item.getCode(),
                              label=enum_item.getSymbol(),
                              meaning=meaning_from_jpype(enum_item.getStandardMeaning()),
                              settable=enum_item.isSettable())

        if typename == 'enum':
            return enum_item_to_obj(val.getEnumItem())
        elif typename == 'enumset':
            return [enum_item_to_obj(v) for v in val.getEnumItemSet()]
        else:
            return super()._convertSimpleValToPy(val)

    _instance = None
