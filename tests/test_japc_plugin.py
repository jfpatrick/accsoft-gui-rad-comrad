import pytest
import logging
import numpy as np
from pathlib import Path
from unittest import mock
from typing import cast, List
from logging import LogRecord
from pytestqt.qtbot import QtBot
from _pytest.logging import LogCaptureFixture
from qtpy.QtCore import Signal, Slot, QObject
from comrad.data import japc_plugin, channel
from comrad import CApplication
from comrad.rbac import CRBACLoginStatus, CRBACStartupLoginPolicy
from _comrad.comrad_info import COMRAD_DEFAULT_PROTOCOL


@pytest.fixture(autouse=True)
def reset_singleton():
    japc_plugin._japc = None
    yield
    japc_plugin._japc = None


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
def test_japc_singleton(_):
    obj1 = japc_plugin.get_japc()
    obj2 = japc_plugin.get_japc()
    assert obj1 is obj2


@pytest.mark.parametrize('succeeds,by_location,expected_status', [
    (True, True, CRBACLoginStatus.LOGGED_IN_BY_LOCATION),
    (False, True, CRBACLoginStatus.LOGGED_OUT),
    (True, False, CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS),
    (False, False, CRBACLoginStatus.LOGGED_OUT),
])
@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('comrad.data.japc_plugin._JapcService.rbacLogin')
@mock.patch('comrad.data.japc_plugin._JapcService.rbacGetToken')
def test_rbac_login(rbacGetToken, rbacLogin, _, succeeds: bool, by_location: bool, expected_status: CRBACLoginStatus):
    japc = japc_plugin.get_japc()
    rbac = cast(CApplication, CApplication.instance()).rbac
    assert japc._logged_in is False
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT
    assert rbac.user is None

    def set_logged_in(*_, **__):
        japc._logged_in = succeeds

    rbacLogin.side_effect = set_logged_in
    rbacGetToken.return_value.getUser.return_value.getName.return_value = 'TEST_USER'

    if by_location:
        japc.login_by_location()
    else:
        japc.login_by_credentials(username='fakeuser', password='fakepasswd')
    rbacLogin.assert_called_once()
    if succeeds:
        rbacGetToken.assert_called_once()
        assert rbac.user == 'TEST_USER'
    else:
        rbacGetToken.assert_not_called()
        assert rbac.user is None
    assert rbac.status == expected_status


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.rbacLogout')
@mock.patch('comrad.data.japc_plugin._JapcService.rbacGetToken')
def test_rbac_logout_succeeds(_, rbacLogout, __):
    japc = japc_plugin.get_japc()
    japc._logged_in = True
    rbac = cast(CApplication, CApplication.instance()).rbac
    rbac.user = 'TEST_USER'
    rbac._status = CRBACLoginStatus.LOGGED_IN_BY_LOCATION

    japc.rbacLogout()
    rbacLogout.assert_called_once()
    japc.rbacGetToken.assert_not_called()
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.rbacLogin')
def test_rbac_login_only_once(rbacLogin, _):
    japc = japc_plugin.get_japc()
    assert japc.logged_in is False

    japc.login_by_location()
    japc.login_by_location()
    japc.login_by_location()
    japc.login_by_location()
    assert japc.logged_in is True
    rbacLogin.assert_called_once()


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.rbacLogout')
def test_rbac_logout_only_once(rbacLogout, _):
    japc = japc_plugin.get_japc()
    japc._logged_in = True
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    assert japc.logged_in is False
    rbacLogout.assert_called_once()


# TODO: Test case with login by credentials when appropriate dialog is implemented
@pytest.mark.parametrize('login_policy,args', [
    (CRBACStartupLoginPolicy.LOGIN_BY_LOCATION, {}),
    (CRBACStartupLoginPolicy.NO_LOGIN, None),
])
@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('comrad.data.japc_plugin._JapcService.rbacLogin')
def test_rbac_login_on_startup(rbacLogin, _, login_policy, args):
    rbac = cast(CApplication, CApplication.instance()).rbac
    rbac.startup_login_policy = login_policy
    japc = japc_plugin.get_japc()
    if login_policy == CRBACStartupLoginPolicy.NO_LOGIN:
        rbacLogin.assert_not_called()
    else:
        rbacLogin.assert_called_once_with(**args, on_exception=japc._login_err)


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.rbacLogin')
def test_rbac_login_notifies_status(_, __, qtbot):
    japc = japc_plugin.get_japc()
    assert japc.logged_in is False
    with qtbot.wait_signal(japc.japc_status_changed) as blocker:
        japc.rbacLogin()
    assert blocker.args == [True]
    assert japc.logged_in is True


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.rbacLogout')
def test_rbac_logout_notifies_status(_, __, qtbot):
    japc = japc_plugin.get_japc()
    japc._logged_in = True
    with qtbot.wait_signal(japc.japc_status_changed) as blocker:
        japc.rbacLogout()
    assert blocker.args == [False]
    assert japc.logged_in is False


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.rbacLogin')
def test_rbac_login_fails_on_auth_exception(rbacLogin, _):

    def raise_error(*_, **__):
        # Stays here to have lazy import of jpype
        import jpype
        cern = jpype.JPackage('cern')
        raise jpype.JException(cern.rbac.client.authentication.AuthenticationException)('Test exception')

    rbacLogin.side_effect = raise_error
    japc = japc_plugin.get_japc()
    assert japc.logged_in is False

    callback = mock.Mock()

    japc.rbacLogin(on_exception=callback)
    callback.assert_called_once_with('Test exception', True)


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.getParam', return_value=3)
def test_japc_get_succeeds(getParam, _):
    japc = japc_plugin.get_japc()
    assert japc.getParam('test_addr') == 3
    getParam.assert_called_once_with('test_addr')


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.setParam')
def test_japc_set_succeeds(setParam, _):
    japc = japc_plugin.get_japc()
    japc.setParam('test_addr', 4)
    setParam.assert_called_once_with('test_addr', 4, checkDims=False)


@pytest.mark.parametrize('method,display_popup,value', [
    ('getParam', False, None),
    ('setParam', True, 4),
])
@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.getParam')
@mock.patch('pyjapc.PyJapc.setParam')
def test_japc_get_set_fails_on_cmw_exception(setParam, getParam, _, method, display_popup, value, qtbot):

    def raise_error(parameterName, *args, **__):
        assert parameterName == 'test_addr'
        if value is not None:
            assert args[0] == value  # Test setParam value

        # Stays here to have lazy import of jpype
        import jpype
        cern = jpype.JPackage('cern')
        raise jpype.JException(cern.japc.core.ParameterException)('Test exception')

    getParam.side_effect = raise_error
    setParam.side_effect = raise_error

    japc = japc_plugin.get_japc()
    args = ['test_addr']
    if value is not None:
        args.append(value)
    with qtbot.wait_signal(japc.japc_param_error) as blocker:
        getattr(japc, method)(*args)
    assert blocker.args == ['Test exception', display_popup]


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
def test_jvm_flags_are_passed(_):

    # Make sure common build resolves java version before we mock out that whole jvm library
    import cmmnbuild_dep_manager
    mgr = cmmnbuild_dep_manager.Manager()
    mgr.start_jpype_jvm()

    with mock.patch('jpype.java') as java:
        cast(CApplication, CApplication.instance()).jvm_flags = {
            'FLAG1': 'val1',
            'FLAG2': 2,
        }
        _ = japc_plugin.get_japc()
        java.lang.System.setProperty.assert_any_call('FLAG1', 'val1')
        java.lang.System.setProperty.assert_any_call('FLAG2', '2')


@pytest.mark.parametrize('selector,filter,expected_selector', [
    (None, None, None),
    ('CERN.TEST.SELECTOR', None, 'CERN.TEST.SELECTOR'),
    (None, {'key': 'val', 'key2': 'val2'}, None),
    ('CERN.TEST.SELECTOR', {'key': 'val', 'key2': 'val2'}, None),
])
@pytest.mark.parametrize(f'param_name, expected_meta_field, expected_param_name', [
    ('mydevice/myprop#myfield', None, 'mydevice/myprop#myfield'),
    ('mydevice/myprop', None, 'mydevice/myprop'),
    ('mydevice/myprop#cycleName', 'cycleName', 'mydevice/myprop'),
    ('rda:///mydevice/myprop#myfield', None, 'rda:///mydevice/myprop#myfield'),
    ('rda:///mydevice/myprop', None, 'rda:///mydevice/myprop'),
    ('rda:///mydevice/myprop#cycleName', 'cycleName', 'rda:///mydevice/myprop'),
    ('rda://srv/mydevice/myprop#myfield', None, 'rda://srv/mydevice/myprop#myfield'),
    ('rda://srv/mydevice/myprop', None, 'rda://srv/mydevice/myprop'),
    ('rda://srv/mydevice/myprop#cycleName', 'cycleName', 'rda://srv/mydevice/myprop'),
])
@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.subscribeParam')
def test_connection_address(_, __, param_name, selector, filter, expected_meta_field, expected_param_name, expected_selector):
    ch = channel.PyDMChannel(address=param_name)
    ctx = channel.CContext(selector=selector, data_filters=filter)
    cast(channel.CChannel, ch).context = ctx
    input_addr = ch.address.split('://')[-1]
    with mock.patch(f'comrad.data.japc_plugin.CJapcConnection.add_listener') as add_listener:
        connection = japc_plugin.CJapcConnection(channel=ch, protocol='rda', address=input_addr)
        add_listener.assert_called_once()
    assert connection._pyjapc_param_name == expected_param_name
    if expected_selector is None:
        assert 'timingSelectorOverride' not in connection._japc_additional_args
    else:
        assert connection._japc_additional_args['timingSelectorOverride'] == expected_selector
    if filter is None:
        assert 'dataFilterOverride' not in connection._japc_additional_args
    else:
        assert connection._japc_additional_args['dataFilterOverride'] == filter
    assert connection._meta_field == expected_meta_field


@pytest.mark.parametrize('channel_address', [
    'property#field',
    'device/property@LHC.USER.ALL',
    'device/property#field@LHC.USER.ALL',
])
@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.subscribeParam')
def test_connection_fails_with_wrong_parameter_name(_, __, channel_address, caplog: LogCaptureFixture):
    ch = channel.PyDMChannel(address=channel_address)
    with mock.patch(f'comrad.data.japc_plugin.CJapcConnection.add_listener') as add_listener:
        _ = japc_plugin.CJapcConnection(channel=ch, protocol='rda', address=ch.address)
        add_listener.assert_not_called()
    actual_warnings = [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.ERROR]
    assert actual_warnings == [f'Cannot create connection with invalid parameter name format "{channel_address}"!']


@pytest.mark.parametrize('selector', [
    '@@@',
    'LHS.USER',
])
@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.subscribeParam')
def test_connection_fails_with_wrong_context(_, __, selector, caplog: LogCaptureFixture):
    ch = channel.PyDMChannel(address='device/property')
    cast(channel.CChannel, ch).context = channel.CContext(selector=selector)
    with mock.patch(f'comrad.data.japc_plugin.CJapcConnection.add_listener') as add_listener:
        _ = japc_plugin.CJapcConnection(channel=ch, protocol='rda', address=f'/device/property')
        add_listener.assert_not_called()
    actual_warnings = [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.ERROR]
    assert actual_warnings == [f'Cannot create connection for address "device/property@{selector}"!']


@pytest.mark.skip
@mock.patch('pydm.widgets.channel.PyDMChannel')
def test_remove_listener_disconnects_slots(PyDMChannel):
    pass
    # FIXME: Cant properly mock 'connect'
    # japc = japc_plugin.get_japc()
    # mocker.patch.object(japc, 'stopSubscriptions')
    # mocker.patch.object(PyDMChannel.value_signal, 'connect')
    # _ = japc_plugin.CJapcConnection(channel=PyDMChannel, address='test_addr')
    # PyDMChannel.value_signal.connect.assert_called_once()


@pytest.mark.parametrize('connected', [
    (True),
    (False),
])
@mock.patch('comrad.data.japc_plugin._JapcService')
def test_close_clears_subscriptions(PyJapc, connected):
    ch = channel.PyDMChannel(address='dev/prop#field')
    with mock.patch.object(japc_plugin, 'get_japc', return_value=PyJapc):
        connection = japc_plugin.CJapcConnection(channel=ch, address='dev/prop#field', protocol='rda')
        connection.online = connected
        PyJapc.clearSubscriptions.assert_not_called()
        connection.close()
        PyJapc.clearSubscriptions.assert_called_with(parameterName='dev/prop#field', selector=None)


@pytest.mark.parametrize('other_type,sim_val', [
    (int, 99),
    (float, 52.3),
    (str, 'test'),
    (np.ndarray, np.array([1, 2])),
    (japc_plugin.CChannelData, 99),
    (japc_plugin.CChannelData, 52.3),
    (japc_plugin.CChannelData, 'test'),
    (japc_plugin.CChannelData, np.array([1, 2])),
])
@mock.patch('comrad.data.japc_plugin._JapcService')
def test_all_new_values_are_emitted_with_channel_data(_, other_type, sim_val, qtbot: QtBot):

    class Receiver(QObject):

        @Slot(other_type)
        def value_changed(self, _):
            pass

    receiver = Receiver()
    ch = channel.PyDMChannel(address='device/property', value_slot=receiver.value_changed)
    connection = japc_plugin.CJapcConnection(channel=ch, protocol='japc', address='/device/property')
    with qtbot.wait_signal(connection.new_value_signal) as blocker:
        connection._on_async_get(None, value=sim_val, headerInfo={})  # Simulate emission of a signal
    assert blocker.args == [japc_plugin.CChannelData(value=sim_val, meta_info={})]


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.subscribeParam')
@mock.patch('pyjapc.PyJapc.getParam')
def test_requested_get_returns_same_uuid(getParam, _, __, qtbot: QtBot):
    def side_effect(onValueReceived, **_):
        onValueReceived(None, 3, {})
        return mock.DEFAULT

    getParam.side_effect = side_effect

    ch = channel.PyDMChannel(address='device/property')
    cast(channel.CChannel, ch).request_slot = lambda *_: None
    connection = japc_plugin.CJapcConnection(channel=ch, protocol='rda', address='/device/property')
    with qtbot.wait_signal(connection.requested_value_signal) as blocker:
        connection._requested_get('test-uuid')
    assert blocker.args == [channel.CChannelData(value=3, meta_info={}), 'test-uuid']


@pytest.mark.parametrize('meta_field,header_field', list(japc_plugin.CJapcConnection.SPECIAL_FIELDS.items()))
@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
def test_meta_field_resolved_on_field_level(_, meta_field, header_field):
    ch = channel.PyDMChannel(address=f'device/property#{meta_field}')
    connection = japc_plugin.CJapcConnection(channel=ch, protocol='rda', address=f'/device/property#{meta_field}')
    callback = mock.Mock()
    sig = mock.MagicMock()
    header = {
        'acqStamp': mock.MagicMock(),
        'setStamp': mock.MagicMock(),
        'cycleStamp': mock.MagicMock(),
        'selector': 'test-cycle-name',
    }
    connection._notify_listeners(f'device/property#{meta_field}', 42, header, signal_handle=callback, callback_signals=[sig])
    callback.assert_called_once_with(sig, channel.CChannelData(value=header[header_field], meta_info=header))


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
def test_meta_field_missing_from_incoming_header(_, caplog: LogCaptureFixture):
    ch = channel.PyDMChannel(address='device/property#acqStamp')
    connection = japc_plugin.CJapcConnection(channel=ch, protocol='rda', address=f'/device/property#acqStamp')
    callback = mock.Mock()
    sig = mock.MagicMock()
    header = {
        'setStamp': mock.MagicMock(),
        'cycleStamp': mock.MagicMock(),
        'selector': 'test-cycle-name',
    }
    connection._notify_listeners(f'device/property#acqStamp', 42, header, signal_handle=callback, callback_signals=[sig])
    # We have to protect from warnings leaking from dependencies, e.g. cmmnbuild_dep_manager, regarding JVM :(
    warning_records = [r for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.WARNING and r.module == 'japc_plugin']
    assert len(warning_records) == 1
    assert 'Cannot locate meta-field "acqStamp" inside packet header' in warning_records[0].msg
    callback.assert_not_called()


@pytest.mark.parametrize('disregarded_header', [{}, {'notSpecial': 'ignore'}])
@pytest.mark.parametrize('val,considered_header,combined_val', [
    ({}, {}, {}),
    ({'val': 42}, {}, {'val': 42}),
    ({'val': 42, 'val2': 'val2'}, {}, {'val': 42, 'val2': 'val2'}),
    ({}, {'acqStamp': 'acqStamp'}, {'acqStamp': 'acqStamp'}),
    ({'val': 42}, {'acqStamp': 'acqStamp'}, {'val': 42, 'acqStamp': 'acqStamp'}),
    ({'val': 42, 'val2': 'val2'}, {'acqStamp': 'acqStamp'}, {'val': 42, 'val2': 'val2', 'acqStamp': 'acqStamp'}),
    ({}, {'selector': 'selector'}, {'cycleName': 'selector'}),
    ({'val': 42}, {'selector': 'selector'}, {'val': 42, 'cycleName': 'selector'}),
    ({'val': 42, 'val2': 'val2'}, {'selector': 'selector'}, {'val': 42, 'val2': 'val2', 'cycleName': 'selector'}),
    ({}, {'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'selector': 'selector'}, {'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'cycleName': 'selector'}),
    ({'val': 42}, {'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'selector': 'selector'}, {'val': 42, 'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'cycleName': 'selector'}),
    ({'val': 42, 'val2': 'val2'}, {'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'selector': 'selector'},
     {'val': 42, 'val2': 'val2', 'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'cycleName': 'selector'}),
    ({'acqStamp': 'valAcqStamp'}, {}, {'acqStamp': 'valAcqStamp'}),
    ({'acqStamp': 'valAcqStamp', 'val2': 'val2'}, {}, {'acqStamp': 'valAcqStamp', 'val2': 'val2'}),
    ({'acqStamp': 'valAcqStamp'}, {'acqStamp': 'acqStamp'}, {'acqStamp': 'acqStamp'}),
    ({'acqStamp': 'valAcqStamp', 'val2': 'val2'}, {'acqStamp': 'acqStamp'}, {'acqStamp': 'acqStamp', 'val2': 'val2'}),
])
@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
def test_meta_fields_are_injected_into_full_property(_, val, considered_header, disregarded_header, combined_val):
    full_header = {**disregarded_header, **considered_header}
    ch = channel.PyDMChannel(address='device/property')
    connection = japc_plugin.CJapcConnection(channel=ch, protocol='japc', address=f'/device/property')
    callback = mock.Mock()
    sig = mock.MagicMock()
    connection._notify_listeners(f'device/property', val, full_header, signal_handle=callback, callback_signals=[sig])
    callback.assert_called_once_with(sig, channel.CChannelData(value=combined_val, meta_info=full_header))


@mock.patch('pyjapc.PyJapc')  # These mocks help against repeated CBNG web-service and "JVM is already started" warnings
@mock.patch('pyjapc.PyJapc.setParam')
def test_write_slots_with_no_params_issue_empty_property_set(setParam, _, qtbot: QtBot):
    class TestWidget(QObject):
        sig = Signal()  # Notice no parameters here, this should be considered as "command"

    sender = TestWidget()
    ch = channel.PyDMChannel(address='device/property', value_signal=sender.sig)
    _ = japc_plugin.CJapcConnection(channel=ch, protocol='japc', address='/device/property')
    with qtbot.wait_signal(sender.sig):
        sender.sig.emit()
    setParam.assert_called_once_with(parameterName='device/property', parameterValue={}, checkDims=False)


@pytest.mark.parametrize('protocol', ['japc', 'rda3', 'rda', 'tgm', 'no'])
def test_japc_plugin_is_used_on_protocols(protocol):
    def custom_env(env_name, *_, **__):
        if env_name == 'PYDM_DATA_PLUGINS_PATH':
            return str(Path(japc_plugin.__file__).parent.absolute())
        return mock.DEFAULT

    from pydm.data_plugins import initialize_plugins_if_needed, plugin_for_address, PyDMPlugin
    import pydm.data_plugins
    pydm.data_plugins.__plugins_initialized = False  # Force to reinitialize

    # In some tests custom environment maybe too late to create (because comrad and, subsequently pydm have already
    # been imported and resolved the environment. So we mock the environment getter for the force re-initialization
    with mock.patch('os.getenv', side_effect=custom_env):
        initialize_plugins_if_needed()
    plugin: PyDMPlugin = plugin_for_address(f'{protocol}:///device/property')
    assert plugin.protocol == protocol
    # Direct comparison does not work because loaded plugin has mangled class path
    assert plugin.connection_class.__name__ == japc_plugin.CJapcConnection.__name__


def test_japc_plugin_is_used_on_no_protocol():
    def custom_env(env_name, *_, **__):
        if env_name == 'PYDM_DATA_PLUGINS_PATH':
            return str(Path(japc_plugin.__file__).parent.absolute())
        return mock.DEFAULT

    from pydm.data_plugins import initialize_plugins_if_needed, plugin_for_address, PyDMPlugin
    import pydm.data_plugins
    pydm.data_plugins.__plugins_initialized = False  # Force to reinitialize
    pydm.data_plugins.config.DEFAULT_PROTOCOL = COMRAD_DEFAULT_PROTOCOL

    # In some tests custom environment maybe too late to create (because comrad and, subsequently pydm have already
    # been imported and resolved the environment. So we mock the environment getter for the force re-initialization
    with mock.patch('os.getenv', side_effect=custom_env):
        initialize_plugins_if_needed()
    plugin: PyDMPlugin = plugin_for_address(f'device/property')
    assert plugin.protocol == COMRAD_DEFAULT_PROTOCOL
    # Direct comparison does not work because loaded plugin has mangled class path
    assert plugin.connection_class.__name__ == japc_plugin.CJapcConnection.__name__
