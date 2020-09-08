import pytest
import os
import logging
from copy import copy
from typing import List, cast
from logging import LogRecord
from _pytest.logging import LogCaptureFixture
from unittest import mock
from pyrbac import Token
from comrad.rbac import CRbaState, CRbaLoginStatus, CRbaToken, CRbaStartupLoginPolicy


def teardown_function():
    # Clean-up all pyrbac environment variables
    for var in ['RBAC_PKEY', 'RBAC_ENV', 'RBAC_APPLICATION_NAME', 'RBAC_TOKEN_SERIALIZED']:
        try:
            del os.environ[var]
        except KeyError:
            pass


def test_logs_on_successful_login(caplog: LogCaptureFixture, qtbot):
    # Make sure the log records are not dismissed
    logging.getLogger().setLevel(logging.NOTSET)

    state = CRbaState()

    def get_logs():
        return [r.getMessage() for r in cast(List[LogRecord], caplog.records) if
                r.levelno == logging.INFO and r.name == 'comrad.rbac']

    assert get_logs() == []
    with qtbot.wait_signal(state._model.login_succeeded):
        state._model.login_succeeded.emit(Token.create_empty_token())
    assert get_logs() == ['RBAC auth successful: ']


@pytest.mark.parametrize('login_method', [
    CRbaToken.LoginMethod.EXPLICIT,
    CRbaToken.LoginMethod.UNKNOWN,
    CRbaToken.LoginMethod.LOCATION,
])
def test_logs_on_failed_login(caplog: LogCaptureFixture, qtbot, login_method):
    state = CRbaState()

    def get_logs():
        return [r.getMessage() for r in cast(List[LogRecord], caplog.records) if
                r.levelno == logging.WARNING and r.name == 'comrad.rbac']

    assert get_logs() == []
    with qtbot.wait_signal(state._model.login_failed):
        state._model.login_failed.emit('Test error', login_method.value)
    assert get_logs() == ['RBAC auth failed: Test error']


def test_logs_on_logout(caplog: LogCaptureFixture, qtbot):
    # Make sure the log records are not dismissed
    logging.getLogger().setLevel(logging.NOTSET)

    state = CRbaState()

    def get_logs():
        return [r.getMessage() for r in cast(List[LogRecord], caplog.records) if
                r.levelno == logging.INFO and r.name == 'comrad.rbac']

    assert get_logs() == []
    with qtbot.wait_signal(state._model.logout_finished):
        state._model.logout_finished.emit()
    assert get_logs() == ['RBAC logout']


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

    state = CRbaState(startup_policy=initial_policy)
    with mock.patch.multiple(state._model, **{name: mock.DEFAULT for name in possible_calls}):
        for name in possible_calls:
            getattr(state._model, name).assert_not_called()
        state.startup_login(initial_token)
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
