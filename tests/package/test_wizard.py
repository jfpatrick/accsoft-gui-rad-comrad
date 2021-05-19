import pytest
from _comrad.package.wizard import validate_email, validate_name, validate_version, validate_arguments


@pytest.mark.parametrize('input,reserved_names', [
    ('pkg1', set()),
    ('pkg1', {'pkg2'}),
    ('pkg1', {'Pkg1'}),
    ('pkg11', {'pkg1', 'pkg2'}),
])
def test_validate_name_succeeds(input, reserved_names):
    assert validate_name(input, reserved_names) is True


@pytest.mark.parametrize('input,reserved_names,expected_error', [
    ('', set(), 'Name cannot be empty'),
    ('', {''}, 'Name cannot be empty'),
    ('', {'pkg1'}, 'Name cannot be empty'),
    ('pkg1', {'pkg1'}, 'Name "pkg1" is reserved for the underlying system.'),
    ('PKG1', {'pkg1'}, 'Name "PKG1" is reserved for the underlying system.'),
    ('pkg2', {'pkg1', 'pkg2'}, 'Name "pkg2" is reserved for the underlying system.'),
    (',./=', {''}, 'Name ",./=" is invalid. Use the name compatible with PEP-508 format.'),
    ('^^^', {'pkg1'}, 'Name "^^^" is invalid. Use the name compatible with PEP-508 format.'),
])
def test_validate_name_fails(input, reserved_names, expected_error):
    assert validate_name(input, reserved_names) == expected_error


@pytest.mark.parametrize('input', [
    '0.0',
    '0.0.1',
    '0.0.1a1',
    'abc',
    '0.0.',
])
def test_validate_version_succeeds(input):
    assert validate_version(input) is True


@pytest.mark.parametrize('input,expected_error', [
    ('', 'Version cannot be empty.'),
    ('0,0', 'Version "0,0" is invalid. Use the PEP-440 format.'),
    ('1,0', 'Version "1,0" is invalid. Use the PEP-440 format.'),
])
def test_validate_version_fails(input, expected_error):
    assert validate_version(input) == expected_error


@pytest.mark.parametrize('input', [
    '',
    'abc@abc',
    'abc@example.com',
])
def test_validate_email_succeeds(input):
    assert validate_email(input) is True


@pytest.mark.parametrize('input,expected_error', [
    ('@', '"@" does not appear to be an email.'),
    ('abc@', '"abc@" does not appear to be an email.'),
    ('@abc', '"@abc" does not appear to be an email.'),
    ('@abc.com', '"@abc.com" does not appear to be an email.'),
])
def test_validate_email_fails(input, expected_error):
    assert validate_email(input) == expected_error


@pytest.mark.parametrize('input', [
    '',
    '--flag',
    '--flag value',
    '--flag=value',
    '--flag value --another-flag',
    '--flag value --another-flag another-value',
    '--flag value --another-flag=another-value',
    '--flag=value --another-flag',
    '--flag=value --another-flag another-value',
    '--flag=value --another-flag=another-value',
    '--flag value -a',
    '--flag value -a another-value',
    '--flag=value -a',
    '--flag=value -a another-value',
    '-f value --another-flag',
    '-f value --another-flag another-value',
    '-f value --another-flag=another-value',
    '--flag val1 val2',
    '--flag val1 val2 --another-flag',
    '--flag val1 val2 --another-flag another-value',
    '--flag val1 val2 --another-flag=another-value',
    '--flag value --another-flag another-val1 another-val2',
    '--flag=value --another-flag another-val1 another-val2',
    '--flag val1 val2 --another-flag another-val1 another-val2',
    '--flag val1 val2 -a',
    '--flag val1 val2 -a another-value',
    '--flag value -a another-val1 another-val2',
    '--flag=value -a another-val1 another-val2',
    '--flag val1 val2 -a another-val1 another-val2',
    '-f val1 val2',
    '-f val1 val2 --another-flag',
    '-f val1 val2 --another-flag another-value',
    '-f val1 val2 --another-flag=another-value',
    '-f value --another-flag another-val1 another-val2',
    '-f val1 val2 --another-flag another-val1 another-val2',
    '-f val1 val2 -a',
    '-f val1 val2 -a another-value',
    '-f value -a another-val1 another-val2',
    '-f val1 val2 -a another-val1 another-val2',
])
def test_validate_arguments_succeeds(input):
    assert validate_arguments(input) is True


@pytest.mark.parametrize('input,expected_error', [
    ('--', '"--" is forbidden in the default arguments.'),
    ('--flag value --', '"--" is forbidden in the default arguments.'),
    ('--flag value -- --another-flag', '"--" is forbidden in the default arguments.'),
    ('--flag value -- --another-flag another-value', '"--" is forbidden in the default arguments.'),
    ('--flag value --another-flag another-value --', '"--" is forbidden in the default arguments.'),
    ('--flag value -- --another-flag another-value --', '"--" is forbidden in the default arguments.'),
    ('--flag value -- -a', '"--" is forbidden in the default arguments.'),
    ('--flag value -- -a another-value', '"--" is forbidden in the default arguments.'),
    ('-f value --another-flag --', '"--" is forbidden in the default arguments.'),
    ('-f value --another-flag another-value --', '"--" is forbidden in the default arguments.'),
    ('-f value -- --another-flag', '"--" is forbidden in the default arguments.'),
    ('-f value -- --another-flag another-value', '"--" is forbidden in the default arguments.'),
    ('-f value -- --another-flag --', '"--" is forbidden in the default arguments.'),
    ('-f value -- --another-flag another-value --', '"--" is forbidden in the default arguments.'),
    ('--flag val1 val2 --', '"--" is forbidden in the default arguments.'),
    ('--flag val1 val2 -- --another-flag', '"--" is forbidden in the default arguments.'),
    ('--flag val1 val2 -- --another-flag another-value', '"--" is forbidden in the default arguments.'),
    ('--flag val1 val2 --another-flag another-value --', '"--" is forbidden in the default arguments.'),
    ('--flag val1 val2 -- --another-flag another-value --', '"--" is forbidden in the default arguments.'),
])
def test_validate_arguments_fails(input, expected_error):
    assert validate_arguments(input) == expected_error
