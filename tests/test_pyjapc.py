import pytest
import logging
from logging import LogRecord
from _pytest.logging import LogCaptureFixture
from pytestqt.qtbot import QtBot
from unittest import mock
from typing import cast, List
from pyrbac import Token
from comrad import CApplication
from comrad.data.pyjapc_patch import CPyJapc


@pytest.fixture(autouse=True)
def mock_pyjapc():
    # Because unittest.mock is unable to fully mock superclass (especially in the multiple inheritance case),
    # we have to mock all super methods manually.

    # Make sure common build resolves java version before we mock out that whole jvm library
    # Pay attention that your jars are downloaded. It sometimes happened to me, that jar directory stayed empty
    # and common build would not resolve it. In this case, you get strange errors, e.g. Java exceptions
    # not deriving from Python BaseException, but the real reason is that real Java classes from cern package
    # are not loaded...
    import cmmnbuild_dep_manager
    mgr = cmmnbuild_dep_manager.Manager('pyjapc')
    mgr.start_jpype_jvm()

    # Call the real thing, just to get pointers to the real types
    import jpype
    cern = jpype.JPackage('cern')
    java = jpype.JPackage('java')

    # In code, we interact with following exceptions:
    # 1. cern.japc.core.ParameterException
    # 2. cern.japc.value.ValueConversionException
    # 3. cern.rbac.client.authentication.AuthenticationException
    # They can't be mocks, because otherwise Python interpreter complains at the except statement.
    # We have to keep these real, while mock everything else.
    ParameterException = cern.japc.core.ParameterException
    ValueConversionException = cern.japc.value.ValueConversionException
    AuthenticationException = cern.rbac.client.authentication.AuthenticationException
    TokenFormatException = cern.rbac.common.TokenFormatException
    # Now the same things with the standard Java exceptions, because they are used in tests as well
    IllegalStateException = java.lang.IllegalStateException
    RuntimeException = java.lang.RuntimeException

    def mock_all_but_known_exceptions(pkg_name):
        # This method mocks java modules imported through jpype.JPackage
        # It helps preventing calls to InCA configurator in PyJapc init methods,
        # or e.g. accessing log4j in JVM setup.

        # Following the statements above, we must keep original exceptions
        # We use recursive call to allow import on any level, e.g. JPackage('cern') or JPackage('cern.japc.core')
        # leading to the mock that would still contain correct exception type at the given path.
        if pkg_name == 'cern.japc.core.ParameterException':
            return ParameterException
        if pkg_name == 'cern.japc.value.ValueConversionException':
            return ValueConversionException
        if pkg_name == 'cern.rbac.client.authentication.AuthenticationException':
            return AuthenticationException
        if pkg_name == 'cern.rbac.client.authentication':
            m = mock.MagicMock()
            m.AuthenticationException = mock_all_but_known_exceptions(f'{pkg_name}.AuthenticationException')
            return m
        if pkg_name == 'cern.rbac.client':
            m = mock.MagicMock()
            m.authentication = mock_all_but_known_exceptions(f'{pkg_name}.authentication')
            return m
        if pkg_name == 'cern.rbac.common.TokenFormatException':
            return TokenFormatException
        if pkg_name == 'cern.rbac.common':
            m = mock.MagicMock()
            m.TokenFormatException = mock_all_but_known_exceptions(f'{pkg_name}.TokenFormatException')
            return mock
        if pkg_name == 'cern.rbac':
            m = mock.MagicMock()
            m.client = mock_all_but_known_exceptions(f'{pkg_name}.client')
            m.common = mock_all_but_known_exceptions(f'{pkg_name}.common')
            return m
        if pkg_name == 'cern.japc.core':
            m = mock.MagicMock()
            m.ParameterException = mock_all_but_known_exceptions(f'{pkg_name}.ParameterException')
            return m
        if pkg_name == 'cern.japc.value':
            m = mock.MagicMock()
            m.ValueConversionException = mock_all_but_known_exceptions(f'{pkg_name}.ValueConversionException')
            return m
        if pkg_name == 'cern.japc':
            m = mock.MagicMock()
            m.core = mock_all_but_known_exceptions(f'{pkg_name}.core')
            m.value = mock_all_but_known_exceptions(f'{pkg_name}.value')
            return m
        if pkg_name == 'cern':
            m = mock.MagicMock()
            m.japc = mock_all_but_known_exceptions(f'{pkg_name}.japc')
            m.rbac = mock_all_but_known_exceptions(f'{pkg_name}.rbac')
            return m
        if pkg_name == 'java.lang.IllegalStateException':
            return IllegalStateException
        if pkg_name == 'java.lang.RuntimeException':
            return RuntimeException
        if pkg_name == 'java.lang':
            m = mock.MagicMock()
            m.core = mock_all_but_known_exceptions(f'{pkg_name}.IllegalStateException')
            m.value = mock_all_but_known_exceptions(f'{pkg_name}.RuntimeException')
            return m
        if pkg_name == 'java':
            m = mock.MagicMock()
            m.japc = mock_all_but_known_exceptions(f'{pkg_name}.lang')
            return m
        return mock.DEFAULT

    with mock.patch('jpype.JPackage', side_effect=mock_all_but_known_exceptions):
        # Here is the real meat. Since we can't mock superclass, we mock all possible used methods of PyJapc
        # This must be done before the first import of comrad.data.pyjapc_patch
        with mock.patch.multiple('comrad.data.pyjapc_patch.PyJapc',
                                 getParam=mock.DEFAULT,
                                 setParam=mock.DEFAULT,
                                 subscribeParam=mock.DEFAULT,
                                 rbacLogin=mock.DEFAULT,
                                 rbacLogout=mock.DEFAULT,
                                 rbacGetToken=mock.DEFAULT):
            from comrad.data.pyjapc_patch import PyJapc
            PyJapc.__del__ = mock.Mock()  # Avoid calling clearSubscriptions and other nonsense at the end of the test
            yield


def test_japc_singleton():
    from comrad.data.pyjapc_patch import CPyJapc
    obj1 = CPyJapc.instance()
    obj2 = CPyJapc.instance()
    assert obj1 is obj2


@mock.patch('pyjapc.PyJapc.rbacLogout')
@mock.patch('pyjapc.PyJapc.rbacGetToken')
def test_rbac_logout_succeeds(rbacGetToken, rbacLogout):
    japc = CPyJapc()
    japc._logged_in = True
    japc.rbacLogout()
    rbacLogout.assert_called_once()
    rbacGetToken.assert_not_called()


@mock.patch('pyjapc.PyJapc.rbacLogout')
def test_rbac_logout_only_once(rbacLogout):
    japc = CPyJapc()
    japc._logged_in = True
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    assert japc._logged_in is False
    rbacLogout.assert_called_once()


def test_rbac_login_does_not_notify_status(qtbot):
    japc = CPyJapc()
    with qtbot.assert_not_emitted(japc.japc_status_changed):
        japc.rbacLogin()


def test_rbac_logout_notifies_status(qtbot):
    japc = CPyJapc()
    japc._logged_in = True
    with qtbot.wait_signal(japc.japc_status_changed) as blocker:
        japc.rbacLogout()
    assert blocker.args == [False]
    assert japc._logged_in is False


@mock.patch('comrad.data.pyjapc_patch.cern')
@mock.patch('pyjapc.PyJapc.rbacGetToken')
def test_rbac_inject_token_succeeds(rbacGetToken, cern, qtbot):
    japc = CPyJapc()
    assert japc._logged_in is False
    token = Token.create_empty_token()
    java_token = mock.MagicMock()
    cern.rbac.util.holder.ClientTierTokenHolder.setRbaToken.assert_not_called()
    cern.rbac.common.RbaToken.parseAndValidate.assert_not_called()
    cern.rbac.common.RbaToken.parseAndValidate.return_value = java_token
    rbacGetToken.assert_not_called()
    with qtbot.wait_signal(japc.japc_status_changed) as blocker:
        japc._inject_token(token)
    assert blocker.args == [True]
    cern.rbac.common.RbaToken.parseAndValidate.assert_called_once()
    cern.rbac.util.holder.ClientTierTokenHolder.setRbaToken.assert_called_once_with(java_token)
    rbacGetToken.assert_called_once()
    assert japc._logged_in is True


def test_rbac_inject_token_notifies_status(qtbot):
    japc = CPyJapc()
    assert japc._logged_in is False
    token = Token.create_empty_token()
    with qtbot.wait_signal(japc.japc_status_changed) as blocker:
        japc._inject_token(token)
    assert blocker.args == [True]
    assert japc._logged_in is True


@pytest.mark.parametrize('error,expected_error', [
    (RuntimeError('Test error'), 'Java refused generated token: Test error'),
    (RuntimeError, 'Java refused generated token: '),
    (ValueError, 'Java refused generated token: '),
    (ValueError('Test value error'), 'Java refused generated token: Test value error'),
])
@mock.patch('comrad.data.pyjapc_patch.cern')
@mock.patch('pyjapc.PyJapc.rbacGetToken')
def test_rbac_inject_token_python_exception_caught(rbacGetToken, cern, qtbot, caplog: LogCaptureFixture, error, expected_error):
    japc = CPyJapc()
    assert japc._logged_in is False

    def get_records():
        return [r.getMessage() for r in cast(List[LogRecord], caplog.records) if
                r.levelno == logging.ERROR and r.name == 'comrad.japc']

    token = Token.create_empty_token()
    cern.rbac.common.RbaToken.parseAndValidate.side_effect = error
    cern.rbac.util.holder.ClientTierTokenHolder.setRbaToken.assert_not_called()
    rbacGetToken.assert_not_called()
    assert get_records() == []
    with qtbot.assert_not_emitted(japc.japc_status_changed):
        japc._inject_token(token)
    assert get_records() == [expected_error]
    cern.rbac.util.holder.ClientTierTokenHolder.setRbaToken.assert_not_called()
    rbacGetToken.assert_not_called()
    assert japc._logged_in is False


@mock.patch('comrad.data.pyjapc_patch.cern')
@mock.patch('pyjapc.PyJapc.rbacGetToken')
def test_rbac_inject_token_java_exception_caught(rbacGetToken, cern, qtbot, caplog: LogCaptureFixture):
    japc = CPyJapc()
    assert japc._logged_in is False

    def raise_error(*_, **__):
        # We must add a custom method, rather than assigning type directly to side_effect,
        # because Java exception does not have a default Python initializer, causing error
        # TypeError: No matching overloads found for constructor
        # cern.rbac.common.TokenFormatException()
        import jpype
        raise jpype.JPackage('cern.rbac.common.TokenFormatException')('Test exception')

    def get_records():
        return [r.getMessage() for r in cast(List[LogRecord], caplog.records) if
                r.levelno == logging.ERROR and r.name == 'comrad.japc']

    token = Token.create_empty_token()
    cern.rbac.common.RbaToken.parseAndValidate.side_effect = raise_error
    cern.rbac.util.holder.ClientTierTokenHolder.setRbaToken.assert_not_called()
    rbacGetToken.assert_not_called()
    assert get_records() == []
    with qtbot.assert_not_emitted(japc.japc_status_changed):
        japc._inject_token(token)
    assert get_records() == ['Java refused generated token: cern.rbac.common.TokenFormatException: Test exception']
    cern.rbac.util.holder.ClientTierTokenHolder.setRbaToken.assert_not_called()
    rbacGetToken.assert_not_called()
    assert japc._logged_in is False


@mock.patch('comrad.data.pyjapc_patch.CPyJapc._inject_token')
def test_rbac_syncs_rbac_token(inject_token, qtbot: QtBot):
    _ = CPyJapc()
    app = cast(CApplication, CApplication.instance())
    new_token = Token.create_empty_token()
    inject_token.assert_not_called()
    with qtbot.wait_signal(app.rbac._model.login_succeeded):
        app.rbac._model.login_succeeded.emit(new_token)
    inject_token.assert_called_once_with(new_token)


@mock.patch('comrad.data.pyjapc_patch.PyJapcWrapper.getParam', return_value=3)
def test_japc_get_succeeds(getParam):
    japc = CPyJapc()
    assert japc.getParam('test_addr') == 3
    getParam.assert_called_once_with('test_addr')


@mock.patch('pyjapc.PyJapc.setParam')
def test_japc_set_succeeds(setParam):
    japc = CPyJapc()
    japc.setParam('test_addr', 4)
    setParam.assert_called_once_with('test_addr', 4, checkDims=False)


@pytest.mark.parametrize('error_type', [
    'cern.japc.value.ValueConversionException',
    'cern.japc.core.ParameterException',
])
@pytest.mark.parametrize('method,display_popup,value', [
    ('getParam', False, None),
    ('setParam', True, 4),
])
@mock.patch('comrad.data.pyjapc_patch.PyJapcWrapper.getParam')
@mock.patch('pyjapc.PyJapc.setParam')
def test_japc_get_set_fails_on_cmw_exception(setParam, getParam, method, display_popup, value, qtbot, error_type):

    def raise_error(parameterName, *args, **__):
        assert parameterName == 'test_addr'
        if value is not None:
            assert args[0] == value  # Test setParam value
        import jpype
        exc_type = jpype.JPackage(error_type)
        raise exc_type('Something happened --> Test exception')

    getParam.side_effect = raise_error
    setParam.side_effect = raise_error

    japc = CPyJapc()
    args = ['test_addr']
    if value is not None:
        args.append(value)
    with qtbot.wait_signal(japc.japc_param_error) as blocker:
        getattr(japc, method)(*args)
    assert blocker.args == ['Test exception', display_popup]


@pytest.mark.parametrize('error_type', [
    'cern.rbac.client.authentication.AuthenticationException',
    'java.lang.IllegalStateException',
    'java.lang.RuntimeException',
])
@pytest.mark.parametrize('method,display_popup,value', [
    ('getParam', False, None),
    ('setParam', True, 4),
])
@mock.patch('comrad.data.pyjapc_patch.PyJapcWrapper.getParam')
@mock.patch('pyjapc.PyJapc.setParam')
def test_japc_get_set_does_catch_other_java_exception(setParam, getParam, method, display_popup, value, qtbot, error_type):

    def raise_error(parameterName, *args, **__):
        assert parameterName == 'test_addr'
        if value is not None:
            assert args[0] == value  # Test setParam value
        import jpype
        exc_type = jpype.JPackage(error_type)
        raise exc_type('Test exception')

    getParam.side_effect = raise_error
    setParam.side_effect = raise_error

    japc = CPyJapc()
    args = ['test_addr']
    if value is not None:
        args.append(value)
    with qtbot.wait_signal(japc.japc_param_error) as blocker:
        getattr(japc, method)(*args)
    assert blocker.args == ['Test exception', display_popup]


@pytest.mark.parametrize('error_type', [ValueError])
@pytest.mark.parametrize('method,display_popup,value', [
    ('getParam', False, None),
    ('setParam', True, 4),
])
@mock.patch('comrad.data.pyjapc_patch.PyJapcWrapper.getParam')
@mock.patch('pyjapc.PyJapc.setParam')
def test_japc_get_set_does_catch_pyjapc_exception(setParam, getParam, method, display_popup, value, qtbot, error_type):

    def raise_error(parameterName, *args, **__):
        assert parameterName == 'test_addr'
        if value is not None:
            assert args[0] == value  # Test setParam value
        raise error_type('Test exception')

    getParam.side_effect = raise_error
    setParam.side_effect = raise_error

    japc = CPyJapc()
    args = ['test_addr']
    if value is not None:
        args.append(value)
    with qtbot.wait_signal(japc.japc_param_error) as blocker:
        getattr(japc, method)(*args)
    assert blocker.args == ['Test exception', display_popup]


@pytest.mark.parametrize('method,value', [
    ('getParam', None),
    ('setParam', 4),
])
@pytest.mark.parametrize('error_type', [TypeError, RuntimeError, Exception, BaseException])
@mock.patch('comrad.data.pyjapc_patch.PyJapcWrapper.getParam')
@mock.patch('pyjapc.PyJapc.setParam')
def test_japc_get_set_does_not_catch_non_pyjapc_exception(setParam, getParam, method, value, qtbot, error_type):
    getParam.side_effect = error_type
    setParam.side_effect = error_type

    japc = CPyJapc()
    args = ['test_addr']
    if value is not None:
        args.append(value)
    with pytest.raises(error_type):
        with qtbot.assert_not_emitted(japc.japc_param_error):
            getattr(japc, method)(*args)


def test_jvm_flags_are_passed():
    with mock.patch('jpype.java') as java:
        cast(CApplication, CApplication.instance()).jvm_flags = {
            'FLAG1': 'val1',
            'FLAG2': 2,
        }
        _ = CPyJapc()
        java.lang.System.setProperty.assert_any_call('FLAG1', 'val1')
        java.lang.System.setProperty.assert_any_call('FLAG2', '2')
