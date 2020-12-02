import pytest
from unittest import mock
from typing import cast
from comrad import CApplication
from comrad.rbac import CRBACLoginStatus, CRBACStartupLoginPolicy


@pytest.fixture()
def pyjapc_subclass():
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
        if pkg_name == 'cern.rbac':
            m = mock.MagicMock()
            m.client = mock_all_but_known_exceptions(f'{pkg_name}.client')
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
            from comrad.data.pyjapc_patch import CPyJapc, PyJapcWrapper
            CPyJapc.super_mock = PyJapcWrapper  # Keep the pointer for the tests to check for call assertions
            CPyJapc.__del__ = mock.Mock()  # Avoid calling clearSubscriptions and other nonsense at the end of the test
            yield CPyJapc


@pytest.mark.parametrize('succeeds,expected_status', [
    (True, CRBACLoginStatus.LOGGED_IN_BY_LOCATION),
    (False, CRBACLoginStatus.LOGGED_OUT),
])
def test_rbac_login_by_location(pyjapc_subclass, succeeds: bool, expected_status: CRBACLoginStatus):

    japc = pyjapc_subclass()
    with mock.patch.object(japc, 'rbacLogin') as rbacLogin:

        def set_logged_in(*_, **__):
            japc._logged_in = succeeds

        rbacLogin.side_effect = set_logged_in

        rbac = cast(CApplication, CApplication.instance()).rbac
        assert japc._logged_in is False
        assert rbac.status == CRBACLoginStatus.LOGGED_OUT
        assert rbac.user is None

        pyjapc_subclass.super_mock.rbacGetToken.return_value.getUser.return_value.getName.return_value = 'TEST_USER'

        japc.login_by_location()
        rbacLogin.assert_called_once()
        if succeeds:
            pyjapc_subclass.super_mock.rbacGetToken.assert_called_once()
            assert rbac.user == 'TEST_USER'
        else:
            pyjapc_subclass.super_mock.rbacGetToken.assert_not_called()
            assert rbac.user is None
        assert rbac.status == expected_status


def test_rbac_logout_succeeds(pyjapc_subclass):
    japc = pyjapc_subclass()
    japc._logged_in = True
    rbac = cast(CApplication, CApplication.instance()).rbac
    rbac.user = 'TEST_USER'
    rbac._status = CRBACLoginStatus.LOGGED_IN_BY_LOCATION

    japc.rbacLogout()
    pyjapc_subclass.super_mock.rbacLogout.assert_called_once()
    pyjapc_subclass.super_mock.rbacGetToken.assert_not_called()
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT


def test_rbac_login_only_once(pyjapc_subclass):
    japc = pyjapc_subclass()
    assert japc.logged_in is False

    japc.login_by_location()
    japc.login_by_location()
    japc.login_by_location()
    japc.login_by_location()
    assert japc.logged_in is True
    pyjapc_subclass.super_mock.rbacLogin.assert_called_once()


def test_rbac_logout_only_once(pyjapc_subclass):
    japc = pyjapc_subclass()
    japc._logged_in = True
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    japc.rbacLogout()
    assert japc.logged_in is False
    pyjapc_subclass.super_mock.rbacLogout.assert_called_once()


# TODO: Test case with login by credentials when appropriate dialog is implemented
@pytest.mark.parametrize('login_policy,args', [
    (CRBACStartupLoginPolicy.LOGIN_BY_LOCATION, {}),
    (CRBACStartupLoginPolicy.NO_LOGIN, None),
])
def test_rbac_login_on_startup(pyjapc_subclass, login_policy, args):
    rbac = cast(CApplication, CApplication.instance()).rbac
    rbac.startup_login_policy = login_policy
    with mock.patch('comrad.data.pyjapc_patch.CPyJapc.rbacLogin') as rbacLogin:
        japc = pyjapc_subclass()
        if login_policy == CRBACStartupLoginPolicy.NO_LOGIN:
            rbacLogin.assert_not_called()
        else:
            rbacLogin.assert_called_once_with(**args, on_exception=japc._login_err)


def test_rbac_login_notifies_status(pyjapc_subclass, qtbot):
    japc = pyjapc_subclass()
    assert japc.logged_in is False
    with qtbot.wait_signal(japc.japc_status_changed) as blocker:
        japc.rbacLogin()
    assert blocker.args == [True]
    assert japc.logged_in is True


def test_rbac_logout_notifies_status(pyjapc_subclass, qtbot):
    japc = pyjapc_subclass()
    japc._logged_in = True
    with qtbot.wait_signal(japc.japc_status_changed) as blocker:
        japc.rbacLogout()
    assert blocker.args == [False]
    assert japc.logged_in is False


def test_rbac_login_fails_on_auth_exception(pyjapc_subclass):

    def raise_error(*_, **__):
        # We must add a custom method, rather than assigning type directly to side_effect,
        # because Java exception does not have a default Python initializer, causing error
        # TypeError: No matching overloads found for constructor
        # cern.rbac.client.authentication.AuthenticationException()
        import jpype
        raise jpype.JPackage('cern.rbac.client.authentication.AuthenticationException')('Test exception')

    pyjapc_subclass.super_mock.rbacLogin.side_effect = raise_error
    japc = pyjapc_subclass()
    assert japc.logged_in is False

    callback = mock.Mock()

    japc.rbacLogin(on_exception=callback)
    callback.assert_called_once_with('Test exception', True)


@pytest.mark.parametrize('error_type', [ValueError, TypeError, RuntimeError, Exception])
def test_rbac_login_does_not_catch_python_exception(pyjapc_subclass, error_type):
    pyjapc_subclass.super_mock.rbacLogin.side_effect = error_type
    japc = pyjapc_subclass()
    assert japc.logged_in is False

    callback = mock.Mock()

    with pytest.raises(error_type):
        japc.rbacLogin(on_exception=callback)
    callback.assert_not_called()


@pytest.mark.parametrize('error_type', [
    'cern.japc.value.ValueConversionException',
    'cern.japc.core.ParameterException',
])
@pytest.mark.parametrize('exc_getter', ['get_param_exc_type', 'get_val_exc_type'])
def test_rbac_login_does_not_catch_other_java_exceptions(pyjapc_subclass, exc_getter, error_type):
    import jpype
    exc_type = jpype.JPackage(error_type)

    pyjapc_subclass.super_mock.rbacLogin.side_effect = exc_type
    japc = pyjapc_subclass()
    assert japc.logged_in is False

    callback = mock.Mock()

    with pytest.raises(exc_type):
        japc.rbacLogin(on_exception=callback)
    callback.assert_not_called()


def test_japc_get_succeeds(pyjapc_subclass):
    pyjapc_subclass.super_mock.getParam.return_value = 3
    japc = pyjapc_subclass()
    assert japc.getParam('test_addr') == 3
    pyjapc_subclass.super_mock.getParam.assert_called_once_with('test_addr')


def test_japc_set_succeeds(pyjapc_subclass):
    japc = pyjapc_subclass()
    japc.setParam('test_addr', 4)
    pyjapc_subclass.super_mock.setParam.assert_called_once_with('test_addr', 4, checkDims=False)


@pytest.mark.parametrize('error_type', [
    'cern.japc.value.ValueConversionException',
    'cern.japc.core.ParameterException',
])
@pytest.mark.parametrize('method,display_popup,value', [
    ('getParam', False, None),
    ('setParam', True, 4),
])
def test_japc_get_set_fails_on_cmw_exception(pyjapc_subclass, method, display_popup, value, qtbot, error_type):

    def raise_error(parameterName, *args, **__):
        assert parameterName == 'test_addr'
        if value is not None:
            assert args[0] == value  # Test setParam value
        import jpype
        exc_type = jpype.JPackage(error_type)
        raise exc_type('Something happened --> Test exception')

    pyjapc_subclass.super_mock.getParam.side_effect = raise_error
    pyjapc_subclass.super_mock.setParam.side_effect = raise_error

    japc = pyjapc_subclass()
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
def test_japc_get_set_does_catch_other_java_exception(pyjapc_subclass, method, display_popup, value, qtbot, error_type):

    def raise_error(parameterName, *args, **__):
        assert parameterName == 'test_addr'
        if value is not None:
            assert args[0] == value  # Test setParam value
        import jpype
        exc_type = jpype.JPackage(error_type)
        raise exc_type('Test exception')

    pyjapc_subclass.super_mock.getParam.side_effect = raise_error
    pyjapc_subclass.super_mock.setParam.side_effect = raise_error

    japc = pyjapc_subclass()
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
@pytest.mark.parametrize('error_type', [ValueError, TypeError, RuntimeError, Exception, BaseException])
def test_japc_get_set_does_not_catch_python_exception(pyjapc_subclass, method, value, qtbot, error_type):
    pyjapc_subclass.super_mock.getParam.side_effect = error_type
    pyjapc_subclass.super_mock.setParam.side_effect = error_type

    japc = pyjapc_subclass()
    args = ['test_addr']
    if value is not None:
        args.append(value)
    with pytest.raises(error_type):
        with qtbot.assert_not_emitted(japc.japc_param_error):
            getattr(japc, method)(*args)


def test_jvm_flags_are_passed(pyjapc_subclass):
    with mock.patch('jpype.java') as java:
        cast(CApplication, CApplication.instance()).jvm_flags = {
            'FLAG1': 'val1',
            'FLAG2': 2,
        }
        _ = pyjapc_subclass()
        java.lang.System.setProperty.assert_any_call('FLAG1', 'val1')
        java.lang.System.setProperty.assert_any_call('FLAG2', '2')
