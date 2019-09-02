from comrad.data import japc_plugin
import pytest
from unittest import mock


def test_japc_singleton():
    obj1 = japc_plugin.get_japc()
    obj2 = japc_plugin.get_japc()
    assert obj1 is obj2


def test_rbac_login_succeeds_by_location(mocker):
    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)
    assert japc._loggedIn is False
    with mocker.patch.object(japc, 'rbacLogin'):
        japc.try_rbac_login()
        assert japc._loggedIn is True
        japc.rbacLogin.assert_called_once_with()


def test_rbac_login_only_once(mocker):
    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)
    assert japc._loggedIn is False
    with mocker.patch.object(japc, 'rbacLogin'):
        japc.try_rbac_login()
        japc.try_rbac_login()
        japc.try_rbac_login()
        japc.try_rbac_login()
        assert japc._loggedIn is True
        japc.rbacLogin.assert_called_once_with()


@mock.patch('pyjapc.PyJapc.rbacLogout')
def test_rbac_logout_only_once(mocked_super):
    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)
    japc._loggedIn = True
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    assert japc._loggedIn is False
    mocked_super.assert_called_once_with()


def test_rbac_login_succeeds_with_dialog(mocker):
    def fake_login(loginDialog=False):
        if not loginDialog:
            raise UserWarning('mock exception')

    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)
    assert japc._loggedIn is False

    with mocker.patch.object(japc, 'rbacLogin', side_effect=fake_login):
        japc.try_rbac_login()
        assert japc._loggedIn is True
        japc.rbacLogin.assert_has_calls([mock.call(), mock.call(loginDialog=True)])


def test_rbac_fails(mocker):
    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)
    assert japc._loggedIn is False

    with mocker.patch.object(japc, 'rbacLogin', side_effect=UserWarning('mock exception')):
        with pytest.raises(UserWarning) as excinfo:
            japc.try_rbac_login()
        assert str(excinfo.value) == 'mock exception'
        assert japc._loggedIn is False
        japc.rbacLogin.assert_has_calls([mock.call(), mock.call(loginDialog=True)])


@mock.patch('pyjapc.PyJapc.setParam')
def test_set_param_fails_without_rbac(mocked_super):
    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)
    japc.setParam('test_addr')
    mocked_super.assert_not_called()


@mock.patch('pyjapc.PyJapc.setParam')
def test_set_param_succeeds_with_rbac(mocked_super, mocker):
    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)
    with mocker.patch.object(japc, 'rbacLogin'):
        japc.try_rbac_login()
        japc.setParam('test_addr')
    mocked_super.assert_called_once()


def test_stop_subscription_does_not_logout_with_active_subscriptions(mocker):
    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)

    class Stub:
        def stopMonitoring(self):
            pass

    stub = Stub()
    with mocker.patch.object(stub, 'stopMonitoring'):
        japc._subscriptionHandleDict['test'] = stub
        with mocker.patch.object(japc, 'rbacLogout'):
            japc.stopSubscriptions(parameterName='another')
            japc.rbacLogout.assert_not_called()


def test_stop_subscription_does_logout_without_active_subscriptions(mocker):
    japc = japc_plugin._JapcService(selector='', incaAcceleratorName=None)
    with mocker.patch.object(japc, 'rbacLogout'):
        japc.stopSubscriptions(parameterName='another')
        japc.rbacLogout.assert_called_once()


@mock.patch('pydm.widgets.channel.PyDMChannel')
def test_connection_address(mocked_channel, mocker):
    with mocker.patch('pyjapc.PyJapc'):
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
    with mocker.patch.object(japc, 'stopSubscriptions'):
        with mocker.patch.object(mocked_channel.value_signal, 'connect'):
            _ = japc_plugin._JapcConnection(channel=mocked_channel, address='test_addr')
            mocked_channel.value_signal.connect.assert_called_once()


@mock.patch('pydm.widgets.channel.PyDMChannel')
def test_close_connected(mocked_channel, mocker):
    japc = japc_plugin.get_japc()
    with mocker.patch.object(japc, 'stopSubscriptions'):
        connection = japc_plugin._JapcConnection(channel=mocked_channel, address='test_addr')
        connection.connected = True
        connection.close()
        japc.stopSubscriptions.assert_called_once()


@mock.patch('pydm.widgets.channel.PyDMChannel')
def test_close_not_connected(mocked_channel, mocker):
    japc = japc_plugin.get_japc()
    with mocker.patch.object(japc, 'stopSubscriptions'):
        connection = japc_plugin._JapcConnection(channel=mocked_channel, address='test_addr')
        connection.connected = False
        connection.close()
        japc.stopSubscriptions.assert_not_called()


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
