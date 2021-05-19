import logging
import pytest
from unittest import mock
from packaging.requirements import Requirement
from _comrad.package.utils import (parse_maintainer_info, make_requirement_safe, find_comrad_requirements,
                                   qualified_pkg_name)


@pytest.mark.parametrize('input,expected_result', [
    (None, (None, None)),
    ('', (None, None)),
    ('John', ('John', '')),
    ('John Smith', ('John Smith', '')),
    ('John.Smith@example.com', ('', 'John.Smith@example.com')),
    ('John Smith <John.Smith@example.com>', ('John Smith', 'John.Smith@example.com')),
    ('John Smith <John.Smith@example.com', (None, None)),
    ('John Smith <>', (None, None)),
    ('<John.Smith@example.com> John Smith', (None, None)),
    ('John.Smith@', ('', 'John.Smith@')),
])
def test_parse_maintainer_info(input, expected_result):
    result = parse_maintainer_info(input)
    assert result == expected_result


@pytest.mark.parametrize('import_name,found_dist_name,expected_req', [
    ('pytest', None, 'pytest'),
    ('pytest>=0.1', None, 'pytest>=0.1'),
    ('pytest<3;python_version<"3.7"', None, 'pytest<3; python_version < "3.7"'),
    ('_comrad', 'comrad', 'comrad'),
    ('_pytest.logging<0.1', 'pytest', 'pytest'),
])
@pytest.mark.parametrize('error', [
    '',
    'Test error',
])
@mock.patch('_comrad.package.utils.find_distribution_name')
def test_make_requirement_safe_succeeds(find_distribution_name, import_name, found_dist_name, expected_req, error):
    find_distribution_name.return_value = found_dist_name
    res = make_requirement_safe(input=import_name, error=error)
    assert res is not None
    assert str(res) == expected_req


@pytest.mark.parametrize('import_name,error,expected_warning', [
    ('???', 'Test error', 'Cannot parse requirement "???". Test error'),
    ('???', '', 'Cannot parse requirement "???". '),
    ('pytest[test,not  what it even that ()]', 'Test error', 'Cannot parse requirement "pytest[test,not  what it even that ()]". Test error'),
    ('pytest[test,not  what it even that ()]', '', 'Cannot parse requirement "pytest[test,not  what it even that ()]". '),
])
@mock.patch('_comrad.package.utils.find_distribution_name', return_value=None)
def test_make_requirement_safe_fails(_, import_name, error, expected_warning, log_capture):
    assert log_capture(logging.WARNING, '_comrad.package.utils') == []
    res = make_requirement_safe(input=import_name, error=error)
    assert res is None
    assert log_capture(logging.WARNING, '_comrad.package.utils') == [expected_warning]


@pytest.mark.parametrize('requires,expected_requires', [
    (None, set()),
    ([], set()),
    (['req1'], {'req1'}),
    (['qasync<1a0,>=0.13.0',
      'pytest-mock<2.1,>=2.0; extra == "test"'], {'qasync<1a0,>=0.13.0'}),
    (['dataclasses~=0.7; python_version < "3.7"',
      'qasync<1a0,>=0.13.0',
      'qasync<1a0,>=0.13.0; extra == "all"',
      'pytest-mock<2.1,>=2.0; extra == "test"'], {'dataclasses~=0.7; python_version < "3.7"', 'qasync<1a0,>=0.13.0'}),
])
@mock.patch('_comrad.package.utils.importlib_metadata')
def test_find_comrad_requirements(importlib_metadata, requires, expected_requires):
    importlib_metadata.distribution.return_value.requires = requires
    res = find_comrad_requirements()
    for r in res:
        assert isinstance(r, Requirement)
    assert set(map(str, res)) == expected_requires


@pytest.mark.parametrize('input,expected_output', [
    ('', ''),
    ('name', 'name'),
    ('Name1', 'Name1'),
    ('dash-name', 'dash_name'),
    ('underline_name', 'underline_name'),
    ('com-bined_name', 'com_bined_name'),
    ('punctu,ation', 'punctu,ation'),
])
def test_qualified_pkg_name(input, expected_output):
    assert qualified_pkg_name(input) == expected_output
