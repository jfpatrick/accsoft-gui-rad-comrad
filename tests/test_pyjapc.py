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
    import cmmnbuild_dep_manager
    mgr = cmmnbuild_dep_manager.Manager('pyjapc')
    mgr.start_jpype_jvm()

    # Call the real thing, just to get pointers to the real types
    import jpype
    cern = jpype.JPackage('cern')

    # In code, we interact with following exceptions:
    # 1. cern.japc.core.ParameterException
    # 2. cern.japc.value.ValueConversionException
    # 3. cern.rbac.client.authentication.AuthenticationException
    # They can't be mocks, because otherwise jpype.JException produces a mock, which is not derivative of BaseException
    # and Python interpreter complains at the except statement. We have to keep these real, while mock everything else
    ParameterException = cern.japc.core.ParameterException
    ValueConversionException = cern.japc.value.ValueConversionException
    AuthenticationException = cern.rbac.client.authentication.AuthenticationException

    def kill_jpype_calls(pkg_name):
        print(f'Getting jpype package {pkg_name}')
        if pkg_name == 'cern':  # Mock callable logic of cern
            cern_mock = mock.MagicMock()
            cern_mock.japc.core.ParameterException = ParameterException
            cern_mock.japc.value.ValueConversionException = ValueConversionException
            cern_mock.rbac.client.authentication.AuthenticationException = AuthenticationException
            return cern_mock
        elif pkg_name == 'org':  # Avoid troubles with log4j
            return mock.MagicMock()
        return mock.DEFAULT

    # minimize the amount of java deps that cmmn_build pulls up, but we still can't have an empty array,
    # since CBNG will complain, so we leave a single package that seems to be the most basic one.
    # in addition, we do need to
    # with mock.patch.multiple('pyjapc', __cmmnbuild_deps__=['japc-ext-inca']):
    #     print(f'Mocked pyjapc Java dependencies')
        # with mock.patch('cmmnbuild_dep_manager.Manager') as mgr_mock:
        #     print(f'Mocked cmmnbuild with {mgr_mock}')
    with mock.patch('jpype.JPackage', side_effect=kill_jpype_calls) as jpype_mock:
        print(f'Mocked jpype top call with {jpype_mock}')
        with mock.patch.multiple('comrad.data.pyjapc_patch.PyJapc',
                                 getParam=mock.DEFAULT,
                                 setParam=mock.DEFAULT,
                                 subscribeParam=mock.DEFAULT,
                                 rbacLogin=mock.DEFAULT,
                                 rbacLogout=mock.DEFAULT,
                                 rbacGetToken=mock.DEFAULT) as mocked_pyjapc:
            print(f'Importing CPyJapc')
            from comrad.data.pyjapc_patch_patch import CPyJapc, PyJapc
            print(f'Superclass {PyJapc} <=> {mocked_pyjapc} and its methods {PyJapc.getParam}, {PyJapc.rbacLogout}')
            # yield mocked_pyjapc
            CPyJapc.super_mock = PyJapc  # Keep the pointer for the tests to check for call assertions
            CPyJapc.__del__ = mock.Mock()  # Avoid calling clearSubscriptions and other nonsense at the end of the test
            yield CPyJapc


@pytest.mark.parametrize('succeeds,by_location,expected_status', [
    (True, True, CRBACLoginStatus.LOGGED_IN_BY_LOCATION),
    (False, True, CRBACLoginStatus.LOGGED_OUT),
    (True, False, CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS),
    (False, False, CRBACLoginStatus.LOGGED_OUT),
])
def test_rbac_login(pyjapc_subclass, succeeds: bool, by_location: bool, expected_status: CRBACLoginStatus):

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

        if by_location:
            japc.login_by_location()
        else:
            japc.login_by_credentials(username='fakeuser', password='fakepasswd')
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
        # Stays here to have lazy import of jpype
        import jpype
        cern = jpype.JPackage('cern')
        print(f'cern pkg: {cern}')
        raise jpype.JException(cern.rbac.client.authentication.AuthenticationException)('Test exception')

    pyjapc_subclass.super_mock.rbacLogin.side_effect = raise_error
    japc = pyjapc_subclass()
    assert japc.logged_in is False

    callback = mock.Mock()

    japc.rbacLogin(on_exception=callback)
    callback.assert_called_once_with('Test exception', True)


def test_japc_get_succeeds(pyjapc_subclass):
    pyjapc_subclass.super_mock.getParam.return_value = 3
    japc = pyjapc_subclass()
    assert japc.getParam('test_addr') == 3
    pyjapc_subclass.super_mock.getParam.assert_called_once_with('test_addr')


def test_japc_set_succeeds(pyjapc_subclass):
    japc = pyjapc_subclass()
    japc.setParam('test_addr', 4)
    pyjapc_subclass.super_mock.setParam.assert_called_once_with('test_addr', 4, checkDims=False)


@pytest.mark.parametrize('method,display_popup,value', [
    ('getParam', False, None),
    ('setParam', True, 4),
])
def test_japc_get_set_fails_on_cmw_exception(pyjapc_subclass, method, display_popup, value, qtbot):

    def raise_error(parameterName, *args, **__):
        assert parameterName == 'test_addr'
        if value is not None:
            assert args[0] == value  # Test setParam value

        # Stays here to have lazy import of jpype
        import jpype
        cern = jpype.JPackage('cern')
        print(f'Cern type: {cern}')
        print(f'Cern exception type: {cern.japc.core.ParameterException}')
        print(f'Cern exception: {jpype.JException(cern.japc.core.ParameterException)}')
        print(f'Java exception type: {jpype.java.lang.NullPointerException}')
        print(f'Java exception: {jpype.JException(jpype.java.lang.NullPointerException)}')
        raise jpype.JException(cern.japc.core.ParameterException)('Test exception')

    pyjapc_subclass.super_mock.getParam.side_effect = raise_error
    pyjapc_subclass.super_mock.setParam.side_effect = raise_error

    japc = pyjapc_subclass()
    args = ['test_addr']
    if value is not None:
        args.append(value)
    with qtbot.wait_signal(japc.japc_param_error) as blocker:
        getattr(japc, method)(*args)
    assert blocker.args == ['Test exception', display_popup]


def test_jvm_flags_are_passed(pyjapc_subclass):

    # Make sure common build resolves java version before we mock out that whole jvm library
    import cmmnbuild_dep_manager
    mgr = cmmnbuild_dep_manager.Manager()
    mgr.start_jpype_jvm()

    with mock.patch('jpype.java') as java:
        cast(CApplication, CApplication.instance()).jvm_flags = {
            'FLAG1': 'val1',
            'FLAG2': 2,
        }
        _ = pyjapc_subclass()
        java.lang.System.setProperty.assert_any_call('FLAG1', 'val1')
        java.lang.System.setProperty.assert_any_call('FLAG2', '2')