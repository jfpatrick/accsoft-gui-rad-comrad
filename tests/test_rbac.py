import pytest
import logging
from copy import copy
from unittest import mock
from pyrbac import Token
from accwidgets.rbac import RbaButtonModel
from comrad.rbac import CRbaState, CRbaLoginStatus, CRbaToken, CRbaStartupLoginPolicy


def test_logs_on_successful_login(log_capture, qtbot):
    state = CRbaState()
    assert log_capture(logging.INFO, 'comrad.rbac') == []
    with qtbot.wait_signal(state._model.login_succeeded):
        state._model.login_succeeded.emit(Token.create_empty_token())
    assert log_capture(logging.INFO, 'comrad.rbac') == ['RBAC auth successful: ']


@pytest.mark.parametrize('login_method', [
    CRbaToken.LoginMethod.EXPLICIT,
    CRbaToken.LoginMethod.UNKNOWN,
    CRbaToken.LoginMethod.LOCATION,
])
def test_logs_on_failed_login(log_capture, qtbot, login_method):
    state = CRbaState()
    assert log_capture(logging.WARNING, 'comrad.rbac') == []
    with qtbot.wait_signal(state._model.login_failed):
        state._model.login_failed.emit('Test error', login_method.value)
    assert log_capture(logging.WARNING, 'comrad.rbac') == ['RBAC auth failed: Test error']


def test_logs_on_logout(log_capture, qtbot):
    state = CRbaState()
    assert log_capture(logging.INFO, 'comrad.rbac') == []
    with qtbot.wait_signal(state._model.logout_finished):
        state._model.logout_finished.emit()
    assert log_capture(logging.INFO, 'comrad.rbac') == ['RBAC logout']


@pytest.mark.parametrize('token_encoded,expected_result', [
    (b'\x01\x02\x05\x06\x07', 'AQIFBgc='),
    (b'\x07\x04\x06\x08\x05\x06\x04\x06\x08\x04\x03', 'BwQGCAUGBAYIBAM='),
])
@mock.patch('comrad.rbac._mgr.RbaButtonModel')
def test_serialized_token(RbaButtonModel, token_encoded, expected_result):
    RbaButtonModel.return_value.token = mock.MagicMock()
    RbaButtonModel.return_value.token.get_encoded.return_value = token_encoded
    rbac = CRbaState()
    assert rbac.serialized_token == expected_result


@pytest.mark.parametrize('token_exists,token_login_method,expected_status', [
    (True, CRbaToken.LoginMethod.LOCATION, CRbaLoginStatus.LOCATION),
    (True, CRbaToken.LoginMethod.EXPLICIT, CRbaLoginStatus.EXPLICIT),
    (True, CRbaToken.LoginMethod.UNKNOWN, CRbaLoginStatus.UNKNOWN),
    (False, None, CRbaLoginStatus.LOGGED_OUT),
])
@mock.patch('comrad.rbac._mgr.RbaButtonModel')
def test_status(RbaButtonModel, token_exists, token_login_method, expected_status):
    RbaButtonModel.return_value.token = mock.MagicMock() if token_exists else None
    if token_exists:
        RbaButtonModel.return_value.token.login_method = token_login_method
    rbac = CRbaState()
    assert rbac.status == expected_status


@pytest.mark.parametrize('token_exists', [True, False])
@mock.patch('comrad.rbac._mgr.RbaButtonModel')
def test_token(RbaButtonModel, token_exists):
    RbaButtonModel.return_value.token = mock.MagicMock() if token_exists else None
    rbac = CRbaState()
    assert rbac.token is RbaButtonModel.return_value.token


@pytest.mark.parametrize('initial_policy,initial_token,expected_call,expected_args,expected_kwargs', [
    (CRbaStartupLoginPolicy.LOGIN_BY_LOCATION, None, 'login_by_location', None, {'interactively_select_roles': False}),
    (CRbaStartupLoginPolicy.LOGIN_EXPLICIT, None, None, None, None),
    (CRbaStartupLoginPolicy.NO_LOGIN, None, None, None, None),
    (CRbaStartupLoginPolicy.LOGIN_BY_LOCATION, 'AQIFBgc=', 'update_token', ('AQIFBgc=',), None),
    (CRbaStartupLoginPolicy.LOGIN_EXPLICIT, 'AQIFBgc=', 'update_token', ('AQIFBgc=',), None),
    (CRbaStartupLoginPolicy.NO_LOGIN, 'AQIFBgc=', 'update_token', ('AQIFBgc=',), None),
    (CRbaStartupLoginPolicy.LOGIN_BY_LOCATION, 'BwQGCAUGBAYIBAM=', 'update_token', ('BwQGCAUGBAYIBAM=',), None),
    (CRbaStartupLoginPolicy.LOGIN_EXPLICIT, 'BwQGCAUGBAYIBAM=', 'update_token', ('BwQGCAUGBAYIBAM=',), None),
    (CRbaStartupLoginPolicy.NO_LOGIN, 'BwQGCAUGBAYIBAM=', 'update_token', ('BwQGCAUGBAYIBAM=',), None),
])
def test_authenticates_at_startup(initial_policy, initial_token, expected_args, expected_call, expected_kwargs):
    possible_calls = ['update_token', 'login_by_location']
    if expected_call is None:
        forbidden_calls = possible_calls
    else:
        forbidden_calls = copy(possible_calls)
        forbidden_calls.remove(expected_call)

    state = CRbaState(startup_policy=initial_policy, serialized_token=initial_token)
    with mock.patch.multiple(state._model, **{name: mock.DEFAULT for name in possible_calls}):
        for name in possible_calls:
            getattr(state._model, name).assert_not_called()
        state.startup_login()
        for name in forbidden_calls:
            getattr(state._model, name).assert_not_called()
        if expected_call is not None:
            meth = getattr(state._model, expected_call)
            if expected_args is None and expected_kwargs is None:
                meth.assert_called_once_with()
            elif expected_kwargs is None:
                meth.assert_called_once_with(*expected_args)
            elif expected_args is None:
                meth.assert_called_once_with(**expected_kwargs)
            else:
                meth.assert_called_once_with(*expected_args, **expected_kwargs)


def test_replace_model_disconnects_original_model():
    rbac = CRbaState()
    old_model = rbac._model
    assert old_model.receivers(old_model.login_succeeded) == 2
    assert old_model.receivers(old_model.login_failed) == 2
    assert old_model.receivers(old_model.logout_finished) == 2
    new_model = RbaButtonModel()
    rbac.replace_model(new_model)
    assert old_model.receivers(old_model.login_succeeded) == 0
    assert old_model.receivers(old_model.login_failed) == 0
    assert old_model.receivers(old_model.logout_finished) == 0


def test_replace_model_connects_new_model():
    rbac = CRbaState()
    new_model = RbaButtonModel()
    assert new_model.receivers(new_model.login_succeeded) == 0
    assert new_model.receivers(new_model.login_failed) == 0
    assert new_model.receivers(new_model.logout_finished) == 0
    rbac.replace_model(new_model)
    assert new_model.receivers(new_model.login_succeeded) == 2
    assert new_model.receivers(new_model.login_failed) == 2
    assert new_model.receivers(new_model.logout_finished) == 2


@pytest.mark.parametrize('token_exists,expect_copy', [
    (True, True),
    (False, False),
])
def test_replace_model_copies_token(token_exists, expect_copy):
    rbac = CRbaState()
    test_token = mock.MagicMock()
    if token_exists:
        rbac._model._token = test_token
    else:
        assert rbac._model._token is None
    new_model = RbaButtonModel()
    with mock.patch.object(new_model, 'update_token') as update_token:
        rbac.replace_model(new_model)
        if expect_copy:
            update_token.assert_called_once_with(test_token)
        else:
            update_token.assert_not_called()
