import pytest
from unittest import mock
from typing import cast
from comrad.data import japc_plugin
from comrad import CApplication
from comrad.rbac import CRBACLoginStatus, CRBACStartupLoginPolicy


class FakeToken:

    class FakeUser:
        def getName(self) -> str:
            return 'TEST_USER'

    def getUser(self) -> 'FakeToken.FakeUser':
        return FakeToken.FakeUser()


def test_japc_singleton():
    obj1 = japc_plugin.get_japc()
    obj2 = japc_plugin.get_japc()
    assert obj1 is obj2


@pytest.mark.parametrize('succeeds,by_location,expected_status', [
    (True, True, CRBACLoginStatus.LOGGED_IN_BY_LOCATION),
    (False, True, CRBACLoginStatus.LOGGED_OUT),
    (True, False, CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS),
    (False, False, CRBACLoginStatus.LOGGED_OUT),
])
def test_rbac_login(succeeds: bool, by_location: bool, expected_status: CRBACLoginStatus, mocker):
    japc = japc_plugin._JapcService()
    rbac = cast(CApplication, CApplication.instance()).rbac
    assert japc._logged_in is False
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT
    assert rbac.user is None

    def set_logged_in(*_, **__):
        japc._logged_in = succeeds

    login_mock = mock.MagicMock()
    login_mock.side_effect = set_logged_in

    token_mock = mock.MagicMock()
    token_mock.return_value = FakeToken()

    mocker.patch.multiple(japc, rbacLogin=login_mock, rbacGetToken=token_mock)
    if by_location:
        japc.login_by_location()
    else:
        japc.login_by_credentials(username='fakeuser', password='fakepasswd')
    cast(mock.Mock, japc.rbacLogin).assert_called_once()
    if succeeds:
        japc.rbacGetToken.assert_called_once()
        assert rbac.user == 'TEST_USER'
    else:
        japc.rbacGetToken.assert_not_called()
        assert rbac.user is None
    assert rbac.status == expected_status


@mock.patch('pyjapc.PyJapc.rbacLogout')
def test_rbac_logout_succeeds(mocked_super, mocker):
    japc = japc_plugin._JapcService()
    japc._logged_in = True
    rbac = cast(CApplication, CApplication.instance()).rbac
    rbac.user = 'TEST_USER'
    rbac._status = CRBACLoginStatus.LOGGED_IN_BY_LOCATION

    mocker.patch.object(japc, 'rbacGetToken')
    japc.rbacLogout()
    mocked_super.assert_called_once()
    japc.rbacGetToken.assert_not_called()
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT


@mock.patch('pyjapc.PyJapc.rbacLogin')
def test_rbac_login_only_once(mocked_super):
    japc = japc_plugin._JapcService()
    assert japc._logged_in is False

    japc.login_by_location()
    japc.login_by_location()
    japc.login_by_location()
    japc.login_by_location()
    assert japc._logged_in is True
    mocked_super.assert_called_once()


@mock.patch('pyjapc.PyJapc.rbacLogout')
def test_rbac_logout_only_once(mocked_super):
    japc = japc_plugin._JapcService()
    japc._logged_in = True
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    assert japc._logged_in is False
    mocked_super.assert_called_once()


# TODO: Test case with login by credentials
@pytest.mark.parametrize('login_policy,args', [
    (CRBACStartupLoginPolicy.LOGIN_BY_LOCATION, {}),
    (CRBACStartupLoginPolicy.NO_LOGIN, None),
])
@mock.patch('pyjapc.PyJapc.rbacLogin')
def test_rbac_login_on_startup(mocked_super, login_policy, args):
    rbac = cast(CApplication, CApplication.instance()).rbac
    rbac.startup_login_policy = login_policy
    if callable is None:
        _ = japc_plugin._JapcService()
        if callable is None:
            mocked_super.assert_not_called()
        else:
            mocked_super.assert_called_once_with(**args)


@mock.patch('pyjapc.PyJapc.rbacLogin')
def test_rbac_login_notifies_status(_):
    callback = mock.MagicMock()
    japc = japc_plugin._JapcService()
    assert japc.logged_in is False
    japc.japc_status_changed.connect(callback)
    japc.rbacLogin()
    callback.assert_called_once_with(True)


@mock.patch('pyjapc.PyJapc.rbacLogout')
def test_rbac_logout_notifies_status(_):
    callback = mock.MagicMock()
    japc = japc_plugin._JapcService()
    japc.japc_status_changed.connect(callback)
    japc._logged_in = True
    japc.rbacLogout()
    callback.assert_called_once_with(False)


def test_rbac_login_fails_on_auth_exception(mocker):

    def raise_error(*_, **__):
        # Stays here to have lazy import of jpype
        import jpype
        cern = jpype.JPackage('cern')
        raise jpype.JException(cern.rbac.client.authentication.AuthenticationException)('Test exception')

    mocker.patch('pyjapc.PyJapc.rbacLogin', side_effect=raise_error)
    japc = japc_plugin._JapcService()
    assert japc.logged_in is False

    callback = mock.MagicMock()

    japc.rbacLogin(on_exception=callback)
    callback.assert_called_once_with('Test exception', True)


@mock.patch('pyjapc.PyJapc.getParam', return_value=3)
def test_japc_get_succeeds(mocked_super):

    japc = japc_plugin._JapcService()
    assert japc.getParam('test_addr') == 3
    mocked_super.assert_called_once_with('test_addr')


def test_japc_set_succeeds(mocker):

    callback = mock.MagicMock()

    mocker.patch('pyjapc.PyJapc.setParam', side_effect=callback)
    japc = japc_plugin._JapcService()
    japc.setParam('test_addr', 4)
    callback.assert_called_once_with('test_addr', 4, checkDims=False)


@pytest.mark.parametrize('method,display_popup,value', [
    ('getParam', False, None),
    ('setParam', True, 4),
])
def test_japc_get_set_fails_on_cmw_exception(mocker, method, display_popup, value):

    def raise_error(parameterName, *args, **__):
        assert parameterName == 'test_addr'
        if value is not None:
            assert args[0] == value  # Test setParam value

        # Stays here to have lazy import of jpype
        import jpype
        cern = jpype.JPackage('cern')
        raise jpype.JException(cern.japc.core.ParameterException)('Test exception')

    mocker.patch(f'pyjapc.PyJapc.{method}', side_effect=raise_error)
    japc = japc_plugin._JapcService()
    callback = mock.MagicMock()
    japc.japc_param_error.connect(callback)
    args = ['test_addr']
    if value is not None:
        args.append(value)
    getattr(japc, method)(*args)
    callback.assert_called_once_with('Test exception', display_popup)


def test_jvm_flags_are_passed():

    # Make sure common build resolves java version before we mock out that whole jvm library
    import cmmnbuild_dep_manager
    mgr = cmmnbuild_dep_manager.Manager()
    mgr.start_jpype_jvm()

    with mock.patch('jpype.java') as mocked_java:
        cast(CApplication, CApplication.instance()).jvm_flags = {
            'FLAG1': 'val1',
            'FLAG2': 2,
        }
        _ = japc_plugin._JapcService()
        mocked_java.lang.System.setProperty.assert_any_call('FLAG1', 'val1')
        mocked_java.lang.System.setProperty.assert_any_call('FLAG2', '2')


@mock.patch('pydm.widgets.channel.PyDMChannel')
def test_connection_address(mocked_channel, mocker):
    mocker.patch('pyjapc.PyJapc')
    connection = japc_plugin._JapcConnection(channel=mocked_channel, address='mydevice/myprop#myfield@CERN.TEST.SELECTOR')
    assert connection._device_prop == 'mydevice/myprop#myfield'
    assert connection._japc_additional_args['timingSelectorOverride'] == 'CERN.TEST.SELECTOR'
    connection = japc_plugin._JapcConnection(channel=mocked_channel, address='mydevice/myprop#myfield')
    assert connection._device_prop == 'mydevice/myprop#myfield'
    assert 'timingSelectorOverride' not in connection._japc_additional_args
    connection = japc_plugin._JapcConnection(channel=mocked_channel, address='mydevice/myprop@CERN.TEST.SELECTOR')
    assert connection._device_prop == 'mydevice/myprop'
    assert connection._japc_additional_args['timingSelectorOverride'] == 'CERN.TEST.SELECTOR'
    connection = japc_plugin._JapcConnection(channel=mocked_channel, address='mydevice/myprop')
    assert connection._device_prop == 'mydevice/myprop'
    assert 'timingSelectorOverride' not in connection._japc_additional_args


@pytest.mark.skip
@mock.patch('pydm.widgets.channel.PyDMChannel')
def test_remove_listener_disconnects_slots(mocked_channel, mocker):
    # FIXME: Cant properly mock 'connect'
    japc = japc_plugin.get_japc()
    mocker.patch.object(japc, 'stopSubscriptions')
    mocker.patch.object(mocked_channel.value_signal, 'connect')
    _ = japc_plugin._JapcConnection(channel=mocked_channel, address='test_addr')
    mocked_channel.value_signal.connect.assert_called_once()


@pytest.mark.parametrize('connected', [
    (True),
    (False),
])
@mock.patch('pydm.widgets.channel.PyDMChannel')
@mock.patch('pyjapc.PyJapc')
def test_close_stops_subscriptions(mocked_channel, mocked_pyjapc, connected):
    japc_plugin._japc = mocked_pyjapc
    connection = japc_plugin._JapcConnection(channel=mocked_channel, address='dev/prop#field')
    connection.online = connected
    connection.close()
    if connected:
        mocked_pyjapc.stopSubscriptions.assert_called_once()
    else:
        mocked_pyjapc.stopSubscriptions.assert_not_called()


def test_split_device_property():
    res = japc_plugin.split_device_property('japc://dev/prop#field@selector')
    assert res.address == 'japc://dev/prop#field'
    assert res.selector == 'selector'
    res = japc_plugin.split_device_property('japc://dev/prop#field@')
    assert res.address == 'japc://dev/prop#field'
    assert res.selector == ''
    res = japc_plugin.split_device_property('japc://dev/prop#field')
    assert res.address == 'japc://dev/prop#field'
    assert res.selector is None
