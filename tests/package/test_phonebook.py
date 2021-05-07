import sys
import pytest
import logging
import importlib
from collections import namedtuple
from unittest import mock
from _comrad.package.phonebook import suggest_maintainer_info


@pytest.fixture
def mock_optional_libs(freeze_modules):
    for lib in ['pyphonebook', 'ldap']:
        if lib not in sys.modules:
            sys.modules[lib] = mock.MagicMock()
    importlib.invalidate_caches()


@pytest.fixture
def mock_ldap_exceptions(mock_optional_libs):
    import ldap

    class FakeLdapException(Exception):
        pass

    class FakeTimeoutException(Exception):
        pass

    # Need both, otherwise (because we have except statement for both) complains that cannot catch non-exception derived types
    ldap.SERVER_DOWN = FakeLdapException
    ldap.TIMEOUT = FakeTimeoutException


@pytest.mark.parametrize('failing_mod,expect_failure', [
    ('pyphonebook', True),
    ('ldap', True),
    ('logging', False),
])
@pytest.mark.parametrize('default_maintainer', [None, '', 'John Smith'])
@pytest.mark.parametrize('default_email', [None, '', 'John.Smith@example.com'])
@pytest.mark.parametrize('force', [True, False])
@mock.patch('getpass.getuser', return_value='root')
def test_suggest_maintainer_info_fails_to_import_modules(getuser, failing_mod, expect_failure,
                                                         default_email, default_maintainer, force, log_capture,
                                                         sim_import_error, mock_optional_libs):
    sim_import_error(failing_mod)
    actual_result = suggest_maintainer_info(default_maintainer=default_maintainer,
                                            default_email=default_email,
                                            force=force)
    assert actual_result == (default_maintainer, default_email)
    msgs = log_capture(logging.DEBUG, '_comrad.package.phonebook')
    if expect_failure:
        assert msgs == ['Phonebook not accessible. No maintainer info will be suggested.']
        getuser.assert_not_called()
    else:
        assert msgs == ["Won't attempt to obtain information for user: root."]
        getuser.assert_called_once()


@pytest.mark.parametrize('user', [
    'root',
])
@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('default_maintainer,default_email,expected_results', [
    (None, None, (None, None)),
    (None, '', (None, '')),
    (None, 'John.Smith@example.com', (None, 'John.Smith@example.com')),
    ('', None, ('', None)),
    ('John Smith', None, ('John Smith', None)),
])
@mock.patch('getpass.getuser')
def test_suggest_maintainer_info_ignores_certain_usernames(getuser, force, default_email, default_maintainer, expected_results,
                                                           log_capture, mock_optional_libs, user):
    getuser.return_value = user
    actual_result = suggest_maintainer_info(default_maintainer=default_maintainer,
                                            default_email=default_email,
                                            force=force)
    assert actual_result == expected_results
    assert log_capture(logging.DEBUG, '_comrad.package.phonebook') == [f"Won't attempt to obtain information for user: {user}."]


@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('default_maintainer,default_email,expected_results', [
    (None, None, (None, None)),
    (None, '', (None, '')),
    (None, 'John.Smith@example.com', (None, 'John.Smith@example.com')),
    ('', None, ('', None)),
    ('John Smith', None, ('John Smith', None)),
])
@mock.patch('getpass.getuser', return_value='test_user')
def test_suggest_maintainer_info_fails_with_ldap_timeout(_, force, default_email, default_maintainer, expected_results,
                                                         log_capture, mock_ldap_exceptions):
    with mock.patch('pyphonebook.PhoneBook') as PhoneBook:
        import ldap
        PhoneBook.return_value.search_by_login_name.side_effect = ldap.TIMEOUT
        actual_result = suggest_maintainer_info(default_maintainer=default_maintainer,
                                                default_email=default_email,
                                                force=force)
        assert actual_result == expected_results
        assert log_capture(logging.DEBUG, '_comrad.package.phonebook') == ['Obtaining contact information for user: test_user.',
                                                                           'Failed to contact phonebook in a reasonable time.']


@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('default_maintainer,default_email,expected_results', [
    (None, None, (None, None)),
    (None, '', (None, '')),
    (None, 'John.Smith@example.com', (None, 'John.Smith@example.com')),
    ('', None, ('', None)),
    ('John Smith', None, ('John Smith', None)),
])
@mock.patch('getpass.getuser', return_value='test_user')
def test_suggest_maintainer_info_fails_with_ldap_server_down(_, force, default_email, default_maintainer, expected_results,
                                                             log_capture, mock_ldap_exceptions):
    import ldap
    with mock.patch('pyphonebook.PhoneBook', side_effect=ldap.SERVER_DOWN):
        actual_result = suggest_maintainer_info(default_maintainer=default_maintainer,
                                                default_email=default_email,
                                                force=force)
        assert actual_result == expected_results
        assert log_capture(logging.DEBUG, '_comrad.package.phonebook') == ['Obtaining contact information for user: test_user.',
                                                                           'Failed to contact phonebook server.']


@pytest.mark.parametrize('force', [True, False])
@pytest.mark.parametrize('default_maintainer,default_email,expected_results', [
    (None, None, (None, None)),
    (None, '', (None, '')),
    (None, 'John.Smith@example.com', (None, 'John.Smith@example.com')),
    ('', None, ('', None)),
    ('John Smith', None, ('John Smith', None)),
])
@mock.patch('getpass.getuser', return_value='test_user')
def test_suggest_maintainer_info_fails_with_unknown_pyphonebook_error(_, force, default_email, default_maintainer, expected_results,
                                                                      log_capture, mock_optional_libs):
    with mock.patch('pyphonebook.PhoneBook') as PhoneBook:
        PhoneBook.return_value.search_by_login_name.return_value = None
        actual_result = suggest_maintainer_info(default_maintainer=default_maintainer,
                                                default_email=default_email,
                                                force=force)
        assert actual_result == expected_results
        assert log_capture(logging.DEBUG, '_comrad.package.phonebook') == ['Obtaining contact information for user: test_user.',
                                                                           "Unknown pyphonebook error. Bailing out: 'NoneType' object is not subscriptable."]


PhoneBoolResultStub = namedtuple('PhoneBoolResultStub', ['full_name', 'email'])


@pytest.mark.parametrize('results,default_maintainer,default_email,force,expected_results', [
    ([], None, None, False, (None, None)),
    ([], None, None, True, (None, None)),
    ([], None, '', False, (None, '')),
    ([], None, '', True, (None, '')),
    ([], None, 'John.Smith@example.com', False, (None, 'John.Smith@example.com')),
    ([], None, 'John.Smith@example.com', True, (None, 'John.Smith@example.com')),
    ([], '', None, False, ('', None)),
    ([], '', None, True, ('', None)),
    ([], 'John Smith', None, False, ('John Smith', None)),
    ([], 'John Smith', None, True, ('John Smith', None)),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], None, None, False, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], None, None, True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], None, '', False, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], None, '', True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], None, 'Another@example.com', False, ('John Smith', 'Another@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], None, 'Another@example.com', True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], '', None, False, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], '', None, True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], 'Another', None, False, ('Another', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com'])], 'Another', None, True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], None, None, False,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], None, None, True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], None, '', False,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], None, '', True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], None, 'Another@example.com', False,
     ('John Smith', 'Another@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], None, 'Another@example.com', True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], '', None, False,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], '', None, True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], 'Another', None, False,
     ('Another', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith', 'AnotherName'], email=['John.Smith@example.com'])], 'Another', None, True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], None, None, False, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], None, None, True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], None, '', False, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], None, '', True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], None, 'Another@example.com', False, ('John Smith', 'Another@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], None, 'Another@example.com', True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], '', None, False, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], '', None, True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], 'Another', None, False, ('Another', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com', 'AnotherEmail'])], 'Another', None, True, ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], None, None, False,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], None, None, True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], None, '', False,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], None, '', True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], None, 'Another@example.com', False,
     ('John Smith', 'Another@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], None, 'Another@example.com', True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], '', None, False,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], '', None, True,
     ('John Smith', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], 'Another', None, False,
     ('Another', 'John.Smith@example.com')),
    ([PhoneBoolResultStub(full_name=['John Smith'], email=['John.Smith@example.com']), PhoneBoolResultStub(full_name=['Third'], email=['Third@example.com'])], 'Another', None, True,
     ('John Smith', 'John.Smith@example.com')),
])
@mock.patch('getpass.getuser', return_value='test_user')
def test_suggest_maintainer_info_succeeds(_, results, default_email, default_maintainer, force,
                                          expected_results, mock_optional_libs, log_capture):
    with mock.patch('pyphonebook.PhoneBook') as PhoneBook:
        PhoneBook.return_value.search_by_login_name.return_value = results
        actual_result = suggest_maintainer_info(default_maintainer=default_maintainer,
                                                default_email=default_email,
                                                force=force)
        assert actual_result == expected_results
        assert log_capture(logging.DEBUG, '_comrad.package.phonebook') == ['Obtaining contact information for user: test_user.']
