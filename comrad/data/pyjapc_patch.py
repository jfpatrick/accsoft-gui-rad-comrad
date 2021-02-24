"""
This module subclasses PyJapc to fix numerous problems with its insufficient behavior so that
it can be used with ComRAD.
"""
import jpype
import logging
from enum import IntFlag, IntEnum
from typing import cast, Optional, Callable, Any, Dict, List
from qtpy.QtCore import QObject, Signal
from pyjapc import PyJapc
from comrad.rbac import CRBACLoginStatus, CRBACStartupLoginPolicy
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
    pyjapc package. Therefore, we have to implement this logic here, overriding everything...
    but, oh well ¯\_(ツ)_/¯, management approves... (actually PR was even safer to allow backwards compatibility,
    but since we don't need it here, that code is removed).
    This should be used with care, because while it replicates the internal logic of PyJapc, it is drastically
    different from internal logic of PAPC. Thus, when PAPC is injected, this method should never be called.
    """  # noqa: W605
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
    japc_login_error = Signal(str, bool)
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
        PyJapcWrapper.__init__(self,
                               selector='',
                               incaAcceleratorName='' if app.use_inca else None)
        QObject.__init__(self)
        self._logged_in: bool = False
        self._use_inca = app.use_inca
        self._app.rbac.rbac_logout_user.connect(self.rbacLogout)
        self._app.rbac.rbac_token_changed.connect(self._on_token_changed_from_pyrbac)
        self.japc_login_error.connect(self._app.rbac.rbac_on_error)
        self.japc_param_error.connect(self._app.on_control_error)
        logger.debug('JAPC is set up and ready!')

        if app.rbac.startup_login_policy == CRBACStartupLoginPolicy.LOGIN_BY_LOCATION:
            logger.debug('Attempting login by location on the first connection')
            try:
                self.login_by_location()
            except BaseException:  # noqa: B902
                logger.info('Login by location failed. User will have to manually acquire RBAC token.')
        elif app.rbac.startup_login_policy == CRBACStartupLoginPolicy.LOGIN_BY_CREDENTIALS:
            # TODO: Implement presenting a dialog here
            pass

    def login_by_location(self):
        logger.debug('Attempting RBAC login by location (via Java RBAC)')
        self.rbacLogin(on_exception=self._login_err)
        if self._logged_in:
            token = self.rbacGetToken()
            if token:
                self._app.rbac.user = token.getUser().getName()  # FIXME: This is Java call. We need to abstract it into PyRBAC
                self._app.rbac.status = CRBACLoginStatus.LOGGED_IN_BY_LOCATION

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
        logger.debug('Performing RBAC login')
        try:
            super().rbacLogin(username=username,
                              password=password,
                              loginDialog=loginDialog,
                              readEnv=readEnv)
        except jpype.JException as e:
            # We can't catch concrete exceptions in the 'except' clause directly, because Python
            # interpreter will complain when used with PAPC, as cern package won't be loaded,
            # and the exception won't be found. In PAPC scenario, this except block should never be
            # executed, thus avoiding the error.
            if isinstance(e, cern.rbac.client.authentication.AuthenticationException):
                if on_exception is not None:
                    message = get_cmw_user_message(e)
                    login_by_location = not username and not password
                    on_exception(message, login_by_location)
                self._set_online(False)
                return
            else:
                raise e
        self._set_online(True)

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

    def _on_token_changed_from_pyrbac(self, pyrbac_token: list, login_status: int):
        logger.debug('Updating Java-RBAC token with the external token from pyrbac')
        config = cern.rbac.common.RbacConfiguration.getCurrent()
        new_token = cern.rbac.common.RbaToken.parseAndValidate(jpype.java.nio.ByteBuffer.wrap(pyrbac_token), config)
        cern.rbac.util.holder.ClientTierTokenHolder.setRbaToken(new_token)

        actual_token = self.rbacGetToken()
        if actual_token:
            self._set_online(login_status != CRBACLoginStatus.LOGGED_OUT)
            self._app.rbac.user = actual_token.getUser().getName()
            self._app.rbac.status = CRBACLoginStatus(login_status)
        else:
            logger.warning('Failed to get a new token from Java')

    def _set_online(self, logged_in: bool):
        self._logged_in = logged_in
        self.japc_status_changed.emit(logged_in)
        if not logged_in:
            self._app.rbac.status = CRBACLoginStatus.LOGGED_OUT

    def _login_err(self, message: str, login_by_location: bool):
        self.japc_login_error.emit(message, login_by_location)

    def _expect_japc_error(self, fn: Callable, *args, display_popup: bool = False, **kwargs):
        try:
            return fn(*args, **kwargs)
        except jpype.JException as e:
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

    def _setup_jvm(self, log_level: int):
        """Overrides internal PyJapc hook to set any custom JVM flags"""
        super()._setup_jvm(log_level=log_level)
        for name, val in self._app.jvm_flags.items():
            logger.debug(f'Setting extra JVM flag: {name}={val}')
            jpype.java.lang.System.setProperty(name, str(val))  # type: ignore

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
