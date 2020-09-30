import pytest
import logging
from unittest import mock
from logging import LogRecord
from typing import List, cast
from packaging.requirements import Requirement
from _pytest.logging import LogCaptureFixture
from _comrad.package.spec_builder import (make_requirement_safe, _inject_mandatory_requirements,
                                          _specialize_requirements_to_currently_installed, _find_comrad_requirements,
                                          _disable_implicit_requirements)


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
@mock.patch('_comrad.package.spec_builder.find_distribution_name')
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
@mock.patch('_comrad.package.spec_builder.find_distribution_name', return_value=None)
def test_make_requirement_safe_fails(_, import_name, error, expected_warning, caplog: LogCaptureFixture):

    def get_warning_records():
        return [r.getMessage() for r in cast(List[LogRecord], caplog.records) if
                r.levelno == logging.WARNING and r.name == '_comrad.package.spec_builder']

    assert get_warning_records() == []
    res = make_requirement_safe(input=import_name, error=error)
    assert res is None
    assert get_warning_records() == [expected_warning]


@pytest.mark.parametrize(f'freeze_output,initial_reqs,expected_reqs', [
    ('', set(), set()),
    ('', {'req1'}, {'req1'}),
    ('', {'req1', 'req2>0.3'}, {'req1', 'req2>0.3'}),
    ('req1', {'req1', 'req2>0.3'}, {'req1', 'req2>0.3'}),
    ('req3', {'req1', 'req2>0.3'}, {'req1', 'req2>0.3'}),
    ('req1==0.5', {'req1', 'req2>0.3'}, {'req1==0.5', 'req2>0.3'}),
    ('req2==0.5', {'req1', 'req2>0.3'}, {'req1', 'req2==0.5'}),
    ("""req1==0.6
req2==0.5""", {'req1', 'req2>0.3'}, {'req1==0.6', 'req2==0.5'}),
    ("""req1==0.6
req2 @ https://example.com/req2.git#egg=req2""", {'req1', 'req2'}, {'req1==0.6', 'req2@ https://example.com/req2.git#egg=req2'}),
])
@mock.patch('subprocess.check_output')
def test_specialize_requirements_to_currently_installed(check_output, freeze_output, initial_reqs, expected_reqs):
    check_output.return_value.decode.return_value = freeze_output
    requirements = set(map(Requirement, initial_reqs))
    _specialize_requirements_to_currently_installed(requirements)
    assert set(map(str, requirements)) == expected_reqs


@pytest.mark.parametrize('initial_reqs,mandatory_reqs,expected_reqs', [
    (set(), None, set()),
    (set(), set(), set()),
    (set(), {'req1'}, {'req1'}),
    ({'req1'}, {'req2'}, {'req1', 'req2'}),
    ({'req1'}, {'req1==0.5'}, {'req1==0.5'}),
    ({'req1', 'req2'}, {'req1==0.5'}, {'req1==0.5', 'req2'}),
])
def test_inject_mandatory_requirements(initial_reqs, mandatory_reqs, expected_reqs):
    requirements = set(map(Requirement, initial_reqs))
    mandatory = set(map(Requirement, mandatory_reqs)) if mandatory_reqs is not None else None
    _inject_mandatory_requirements(original=requirements, mandatory=mandatory)
    assert set(map(str, requirements)) == expected_reqs


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
@mock.patch('_comrad.package.spec_builder.importlib_metadata')
def test_find_comrad_requirements(importlib_metadata, requires, expected_requires):
    importlib_metadata.distribution.return_value.requires = requires
    res = _find_comrad_requirements()
    for r in res:
        assert isinstance(r, Requirement)
    assert set(map(str, res)) == expected_requires


@pytest.mark.parametrize('reqs,mandatory_reqs,comrad_reqs,expected_implicit,expected_explicit', [
    (set(), None, set(), set(), set()),
    (set(), set(), set(), set(), set()),
    (set(), {'req1'}, set(), set(), set()),
    (set(), {'req1==0.5'}, set(), set(), set()),
    (set(), set(), {'req1'}, set(), set()),
    (set(), set(), {'req1==0.5'}, set(), set()),
    (set(), {'req1'}, {'req1'}, set(), set()),
    (set(), {'req1'}, {'req1==0.5'}, set(), set()),
    (set(), {'req1==0.5'}, {'req1'}, set(), set()),
    (set(), {'req1'}, {'req2'}, set(), set()),
    (set(), {'req1==0.5'}, {'req2'}, set(), set()),
    (set(), {'req1'}, {'req2==0.5'}, set(), set()),
    (set(), {'req1==0.5'}, {'req2==0.5'}, set(), set()),
    (set(), set(), {'req1', 'req2'}, set(), set()),
    (set(), set(), {'req1', 'req2==0.5'}, set(), set()),
    (set(), set(), {'req1==0.5', 'req2'}, set(), set()),
    (set(), set(), {'req1==0.5', 'req2==0.5'}, set(), set()),
    (set(), {'req1'}, {'req1', 'req2'}, set(), set()),
    (set(), {'req1'}, {'req1', 'req2==0.5'}, set(), set()),
    (set(), {'req1'}, {'req1==0.5', 'req2'}, set(), set()),
    (set(), {'req1'}, {'req1==0.5', 'req2==0.5'}, set(), set()),
    (set(), {'req1==0.5'}, {'req1', 'req2'}, set(), set()),
    (set(), {'req1==0.5'}, {'req1', 'req2==0.5'}, set(), set()),
    (set(), {'req1==0.5'}, {'req1==0.5', 'req2'}, set(), set()),
    (set(), {'req1==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), set()),
    (set(), {'req1', 'req2'}, {'req1', 'req2'}, set(), set()),
    (set(), {'req1', 'req2'}, {'req1', 'req2==0.5'}, set(), set()),
    (set(), {'req1', 'req2'}, {'req1==0.5', 'req2'}, set(), set()),
    (set(), {'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), set()),
    (set(), {'req1', 'req2==0.5'}, {'req1', 'req2'}, set(), set()),
    (set(), {'req1', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), set()),
    (set(), {'req1', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), set()),
    (set(), {'req1', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), set()),
    (set(), {'req1==0.5', 'req2'}, {'req1', 'req2'}, set(), set()),
    (set(), {'req1==0.5', 'req2'}, {'req1', 'req2==0.5'}, set(), set()),
    (set(), {'req1==0.5', 'req2'}, {'req1==0.5', 'req2'}, set(), set()),
    (set(), {'req1==0.5', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), set()),
    (set(), {'req1==0.5', 'req2==0.5'}, {'req1', 'req2'}, set(), set()),
    (set(), {'req1==0.5', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), set()),
    (set(), {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), set()),
    (set(), {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), set()),
    (set(), {'req3'}, {'req1', 'req2'}, set(), set()),
    (set(), {'req3'}, {'req1', 'req2==0.5'}, set(), set()),
    (set(), {'req3'}, {'req1==0.5', 'req2'}, set(), set()),
    (set(), {'req3'}, {'req1==0.5', 'req2==0.5'}, set(), set()),
    (set(), {'req3', 'req2==0.5'}, {'req1', 'req2'}, set(), set()),
    (set(), {'req3', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), set()),
    (set(), {'req3', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), set()),
    (set(), {'req3', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), set()),
    ({'req1'}, None, set(), set(), {'req1'}),
    ({'req1'}, set(), set(), set(), {'req1'}),
    ({'req1'}, {'req1'}, set(), set(), {'req1'}),
    ({'req1'}, {'req1==0.5'}, set(), set(), {'req1'}),
    ({'req1'}, set(), {'req1'}, {'req1'}, set()),
    ({'req1'}, set(), {'req1==0.5'}, {'req1==0.5'}, set()),
    ({'req1'}, {'req1'}, {'req1'}, set(), {'req1'}),
    ({'req1'}, {'req1'}, {'req1==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5'}, {'req1'}, set(), {'req1'}),
    ({'req1'}, {'req1'}, {'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5'}, {'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1'}, {'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5'}, {'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, set(), {'req1', 'req2'}, {'req1'}, set()),
    ({'req1'}, set(), {'req1', 'req2==0.5'}, {'req1'}, set()),
    ({'req1'}, set(), {'req1==0.5', 'req2'}, {'req1==0.5'}, set()),
    ({'req1'}, set(), {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, set()),
    ({'req1'}, {'req1'}, {'req1', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1'}, {'req1', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1'}, {'req1==0.5', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5'}, {'req1', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1', 'req2'}, {'req1', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5', 'req2'}, {'req1', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1'}),
    ({'req1'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1'}),
    ({'req1'}, {'req3'}, {'req1', 'req2'}, {'req1'}, set()),
    ({'req1'}, {'req3'}, {'req1', 'req2==0.5'}, {'req1'}, set()),
    ({'req1'}, {'req3'}, {'req1==0.5', 'req2'}, {'req1==0.5'}, set()),
    ({'req1'}, {'req3'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, set()),
    ({'req1'}, {'req3', 'req2==0.5'}, {'req1', 'req2'}, {'req1'}, set()),
    ({'req1'}, {'req3', 'req2==0.5'}, {'req1', 'req2==0.5'}, {'req1'}, set()),
    ({'req1'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2'}, {'req1==0.5'}, set()),
    ({'req1'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, set()),
    ({'req1', 'req2'}, None, set(), set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, set(), set(), set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1'}, set(), set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5'}, set(), set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, set(), {'req1'}, {'req1'}, {'req2'}),
    ({'req1', 'req2'}, set(), {'req1==0.5'}, {'req1==0.5'}, {'req2'}),
    ({'req1', 'req2'}, {'req1'}, {'req1'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1'}, {'req1==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5'}, {'req1'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1'}, {'req2'}, {'req2'}, {'req1'}),
    ({'req1', 'req2'}, {'req1==0.5'}, {'req2'}, {'req2'}, {'req1'}),
    ({'req1', 'req2'}, {'req1'}, {'req2==0.5'}, {'req2==0.5'}, {'req1'}),
    ({'req1', 'req2'}, {'req1==0.5'}, {'req2==0.5'}, {'req2==0.5'}, {'req1'}),
    ({'req1', 'req2'}, set(), {'req1', 'req2'}, {'req2', 'req1'}, set()),
    ({'req1', 'req2'}, set(), {'req1', 'req2==0.5'}, {'req2==0.5', 'req1'}, set()),
    ({'req1', 'req2'}, set(), {'req1==0.5', 'req2'}, {'req2', 'req1==0.5'}, set()),
    ({'req1', 'req2'}, set(), {'req1==0.5', 'req2==0.5'}, {'req2==0.5', 'req1==0.5'}, set()),
    ({'req1', 'req2'}, {'req1'}, {'req1', 'req2'}, {'req2'}, {'req1'}),
    ({'req1', 'req2'}, {'req1'}, {'req1', 'req2==0.5'}, {'req2==0.5'}, {'req1'}),
    ({'req1', 'req2'}, {'req1'}, {'req1==0.5', 'req2'}, {'req2'}, {'req1'}),
    ({'req1', 'req2'}, {'req1'}, {'req1==0.5', 'req2==0.5'}, {'req2==0.5'}, {'req1'}),
    ({'req1', 'req2'}, {'req1==0.5'}, {'req1', 'req2'}, {'req2'}, {'req1'}),
    ({'req1', 'req2'}, {'req1==0.5'}, {'req1', 'req2==0.5'}, {'req2==0.5'}, {'req1'}),
    ({'req1', 'req2'}, {'req1==0.5'}, {'req1==0.5', 'req2'}, {'req2'}, {'req1'}),
    ({'req1', 'req2'}, {'req1==0.5'}, {'req1==0.5', 'req2==0.5'}, {'req2==0.5'}, {'req1'}),
    ({'req1', 'req2'}, {'req1', 'req2'}, {'req1', 'req2'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5', 'req2'}, {'req1', 'req2'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req2'}),
    ({'req1', 'req2'}, {'req3'}, {'req1', 'req2'}, {'req1', 'req2'}, set()),
    ({'req1', 'req2'}, {'req3'}, {'req1', 'req2==0.5'}, {'req1', 'req2==0.5'}, set()),
    ({'req1', 'req2'}, {'req3'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2'}, set()),
    ({'req1', 'req2'}, {'req3'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set()),
    ({'req1', 'req2'}, {'req3', 'req2==0.5'}, {'req1', 'req2'}, {'req1'}, {'req2'}),
    ({'req1', 'req2'}, {'req3', 'req2==0.5'}, {'req1', 'req2==0.5'}, {'req1'}, {'req2'}),
    ({'req1', 'req2'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2'}, {'req1==0.5'}, {'req2'}),
    ({'req1', 'req2'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, {'req2'}),
    ({'req4'}, None, set(), set(), {'req4'}),
    ({'req4'}, set(), set(), set(), {'req4'}),
    ({'req4'}, {'req1'}, set(), set(), {'req4'}),
    ({'req4'}, {'req1==0.5'}, set(), set(), {'req4'}),
    ({'req4'}, set(), {'req1'}, set(), {'req4'}),
    ({'req4'}, set(), {'req1==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1'}, {'req1'}, set(), {'req4'}),
    ({'req4'}, {'req1'}, {'req1==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5'}, {'req1'}, set(), {'req4'}),
    ({'req4'}, {'req1'}, {'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5'}, {'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1'}, {'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5'}, {'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, set(), {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, set(), {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, set(), {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, set(), {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1'}, {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1'}, {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1'}, {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1'}, {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5'}, {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5'}, {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5'}, {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1', 'req2'}, {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5', 'req2'}, {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req3'}, {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req3'}, {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req3'}, {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req3'}, {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req3', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req3', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req4'}),
    ({'req4'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req4'}),
    ({'req4'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req4'}),
    ({'req1', 'req4'}, None, set(), set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, set(), set(), set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1'}, set(), set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5'}, set(), set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, set(), {'req1'}, {'req1'}, {'req4'}),
    ({'req1', 'req4'}, set(), {'req1==0.5'}, {'req1==0.5'}, {'req4'}),
    ({'req1', 'req4'}, {'req1'}, {'req1'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1'}, {'req1==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5'}, {'req1'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1'}, {'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5'}, {'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1'}, {'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5'}, {'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, set(), {'req1', 'req2'}, {'req1'}, {'req4'}),
    ({'req1', 'req4'}, set(), {'req1', 'req2==0.5'}, {'req1'}, {'req4'}),
    ({'req1', 'req4'}, set(), {'req1==0.5', 'req2'}, {'req1==0.5'}, {'req4'}),
    ({'req1', 'req4'}, set(), {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, {'req4'}),
    ({'req1', 'req4'}, {'req1'}, {'req1', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5'}, {'req1', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1', 'req2'}, {'req1', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5', 'req2'}, {'req1', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1', 'req4'}),
    ({'req1', 'req4'}, {'req3'}, {'req1', 'req2'}, {'req1'}, {'req4'}),
    ({'req1', 'req4'}, {'req3'}, {'req1', 'req2==0.5'}, {'req1'}, {'req4'}),
    ({'req1', 'req4'}, {'req3'}, {'req1==0.5', 'req2'}, {'req1==0.5'}, {'req4'}),
    ({'req1', 'req4'}, {'req3'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, {'req4'}),
    ({'req1', 'req4'}, {'req3', 'req2==0.5'}, {'req1', 'req2'}, {'req1'}, {'req4'}),
    ({'req1', 'req4'}, {'req3', 'req2==0.5'}, {'req1', 'req2==0.5'}, {'req1'}, {'req4'}),
    ({'req1', 'req4'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2'}, {'req1==0.5'}, {'req4'}),
    ({'req1', 'req4'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, {'req4'}),
    ({'req1==0.5', 'req4'}, None, set(), set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, set(), set(), set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, set(), set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5'}, set(), set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, set(), {'req1'}, {'req1'}, {'req4'}),
    ({'req1==0.5', 'req4'}, set(), {'req1==0.5'}, {'req1==0.5'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, {'req1'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, {'req1==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5'}, {'req1'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, {'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5'}, {'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, {'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5'}, {'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, set(), {'req1', 'req2'}, {'req1'}, {'req4'}),
    ({'req1==0.5', 'req4'}, set(), {'req1', 'req2==0.5'}, {'req1'}, {'req4'}),
    ({'req1==0.5', 'req4'}, set(), {'req1==0.5', 'req2'}, {'req1==0.5'}, {'req4'}),
    ({'req1==0.5', 'req4'}, set(), {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, {'req1', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, {'req1', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, {'req1==0.5', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5'}, {'req1', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1', 'req2'}, {'req1', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5', 'req2'}, {'req1', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5', 'req2'}, {'req1', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5', 'req2'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, set(), {'req1==0.5', 'req4'}),
    ({'req1==0.5', 'req4'}, {'req3'}, {'req1', 'req2'}, {'req1'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req3'}, {'req1', 'req2==0.5'}, {'req1'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req3'}, {'req1==0.5', 'req2'}, {'req1==0.5'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req3'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req3', 'req2==0.5'}, {'req1', 'req2'}, {'req1'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req3', 'req2==0.5'}, {'req1', 'req2==0.5'}, {'req1'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2'}, {'req1==0.5'}, {'req4'}),
    ({'req1==0.5', 'req4'}, {'req3', 'req2==0.5'}, {'req1==0.5', 'req2==0.5'}, {'req1==0.5'}, {'req4'}),
])
@mock.patch('_comrad.package.spec_builder._find_comrad_requirements')
def test_disable_implicit_requirements(find_comrad_requirements, reqs, mandatory_reqs, comrad_reqs, expected_explicit, expected_implicit):
    find_comrad_requirements.return_value = set(map(Requirement, comrad_reqs))
    requires = set(map(Requirement, reqs))
    mandatory = set(map(Requirement, mandatory_reqs)) if mandatory_reqs is not None else None
    res = _disable_implicit_requirements(input=requires, mandatory=mandatory)
    assert set(map(str, res)) == expected_implicit
    assert set(map(str, requires)) == expected_explicit
