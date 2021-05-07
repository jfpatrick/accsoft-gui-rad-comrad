import pytest
import logging
from pathlib import Path
from unittest import mock
from packaging.requirements import Requirement
from _comrad.package.spec_builder import (_generate_pyproject_with_spec_unsafe, _inject_mandatory_requirements,
                                          _specialize_requirements_to_currently_installed, _find_comrad_requirements,
                                          _disable_implicit_requirements, generate_pyproject_with_spec, PackageSpec,
                                          COMRAD_PINNED_VERSION, InvalidProjectFileError, make_requirement_safe)


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
def test_make_requirement_safe_fails(_, import_name, error, expected_warning, log_capture):
    assert log_capture(logging.WARNING, '_comrad.package.spec_builder') == []
    res = make_requirement_safe(input=import_name, error=error)
    assert res is None
    assert log_capture(logging.WARNING, '_comrad.package.spec_builder') == [expected_warning]


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


@pytest.mark.parametrize('force_phonebook', [True, False])
@pytest.mark.parametrize('interactive,cached_spec,cli_other_spec_props,cli_install_requires,scanned_requires,interactive_mods,expected_requires,expected_name,expected_version,expected_maintainer,expected_email,expected_description', [
    (False, InvalidProjectFileError, None, None, set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', None, None, None),
    (False, InvalidProjectFileError, None, set(), set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', None, None, None),
    (False, InvalidProjectFileError, None, {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'app', '0.0.1', None, None, None),
    (False, {}, None, None, set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', None, None, None),
    (False, {}, None, set(), set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', None, None, None),
    (False, {}, None, {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'app', '0.0.1', None, None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}, None, None, set(), None, {COMRAD_PINNED_VERSION}, 'custom', '0.0.1', None, None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}, None, set(), set(), None, {COMRAD_PINNED_VERSION}, 'custom', '0.0.1', None, None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}, None,
     {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'custom', '0.0.1', None, None, None),
    (False, InvalidProjectFileError, {'name': 'cliname'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (False, InvalidProjectFileError, {'name': 'cliname'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (False, InvalidProjectFileError, {'name': 'cliname'}, {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'cliname', '0.0.1', None, None, None),
    (False, {}, {'name': 'cliname'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (False, {}, {'name': 'cliname'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (False, {}, {'name': 'cliname'}, {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'cliname', '0.0.1', None, None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname'}, {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'cliname', '0.0.1', None, None, None),
    (False, InvalidProjectFileError, {'maintainer': 'John'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', 'John', None, None),
    (False, InvalidProjectFileError, {'maintainer': 'John'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', 'John', None, None),
    (False, InvalidProjectFileError, {'maintainer': 'John'}, {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'app', '0.0.1', 'John', None, None),
    (False, {}, {'maintainer': 'John'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', 'John', None, None),
    (False, {}, {'maintainer': 'John'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', 'John', None, None),
    (False, {}, {'maintainer': 'John'}, {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'app', '0.0.1', 'John', None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'maintainer': 'John'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'custom', '0.0.1', 'John', None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'maintainer': 'John'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'custom', '0.0.1', 'John', None, None),
    (False, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'maintainer': 'John'}, {'tensorflow'}, set(), None, {COMRAD_PINNED_VERSION, 'tensorflow'}, 'custom', '0.0.1', 'John', None, None),
    (True, InvalidProjectFileError, {'name': 'cliname'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname'}, set(), set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'},
     'cliname', '0.0.1', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}},
     {COMRAD_PINNED_VERSION, 'pytest'}, 'cliname', '0.0.1', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname'}, {'tensorflow==1.0'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}},
     {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'cliname', '0.0.1', None, None, None),
    (True, {}, {'name': 'cliname'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (True, {}, {'name': 'cliname'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (True, {}, {'name': 'cliname'}, set(), set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'},
     'cliname', '0.0.1', None, None, None),
    (True, {}, {'name': 'cliname'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'},
     'cliname', '0.0.1', None, None, None),
    (True, {}, {'name': 'cliname'}, {'tensorflow==1.0'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}},
     {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'cliname', '0.0.1', None, None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.1', None, None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'}, 'cliname', '0.0.1', None, None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname'}, {'tensorflow==1.0'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}}, {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'cliname', '0.0.1', None, None, None),
    (True, InvalidProjectFileError, {'maintainer': 'John'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', 'John', None, None),
    (True, InvalidProjectFileError, {'maintainer': 'John'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', 'John', None, None),
    (True, InvalidProjectFileError, {'maintainer': 'John'}, set(), set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}},
     {COMRAD_PINNED_VERSION, 'pytest'}, 'app', '0.0.1', 'John', None, None),
    (True, InvalidProjectFileError, {'maintainer': 'John'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}},
     {COMRAD_PINNED_VERSION, 'pytest'}, 'app', '0.0.1', 'John', None, None),
    (True, InvalidProjectFileError, {'maintainer': 'John'}, {'tensorflow==1.0'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}},
     {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'app', '0.0.1', 'John', None, None),
    (True, {}, {'maintainer': 'John'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', 'John', None, None),
    (True, {}, {'maintainer': 'John'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'app', '0.0.1', 'John', None, None),
    (True, {}, {'maintainer': 'John'}, set(), set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'},
     'app', '0.0.1', 'John', None, None),
    (True, {}, {'maintainer': 'John'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'},
     'app', '0.0.1', 'John', None, None),
    (True, {}, {'maintainer': 'John'}, {'tensorflow==1.0'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}},
     {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'app', '0.0.1', 'John', None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'maintainer': 'John'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'custom', '0.0.1', 'John', None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'maintainer': 'John'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'custom', '0.0.1', 'John', None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'maintainer': 'John'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'}, 'custom', '0.0.1', 'John', None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'maintainer': 'John'}, {'tensorflow==1.0'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}}, {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'custom', '0.0.1', 'John', None, None),
    (True, InvalidProjectFileError, {'name': 'cliname', 'version': '0.0.2'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.2', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname', 'version': '0.0.2'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.2', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname', 'version': '0.0.2'}, set(), set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}},
     {COMRAD_PINNED_VERSION, 'pytest'}, 'cliname', '0.0.2', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'}, 'cliname', '0.0.2', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow==1.0'}, set(),
     {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}}, {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'cliname', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, set(), set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}},
     {COMRAD_PINNED_VERSION, 'pytest'}, 'cliname', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}},
     {COMRAD_PINNED_VERSION, 'pytest'}, 'cliname', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow==1.0'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}},
     {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'cliname', '0.0.2', None, None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname', 'version': '0.0.2'}, None, set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.2', None, None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname', 'version': '0.0.2'}, set(), set(), None, {COMRAD_PINNED_VERSION}, 'cliname', '0.0.2', None, None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'pytest'}}, {COMRAD_PINNED_VERSION, 'pytest'}, 'cliname', '0.0.2', None, None, None),
    (True, {'project': {'name': 'custom', 'version': '0.0.1', 'dependencies': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow==1.0'}, set(), {'install_requires': {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}}, {COMRAD_PINNED_VERSION, 'tensorflow==2.0'}, 'cliname', '0.0.2', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname', 'version': '0.0.2'}, set(), set(), {'name': 'interactivename'},
     {COMRAD_PINNED_VERSION}, 'interactivename', '0.0.2', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow'}, set(), {'name': 'interactivename'},
     {COMRAD_PINNED_VERSION, 'tensorflow'}, 'interactivename', '0.0.2', None, None, None),
    (True, InvalidProjectFileError, {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow==1.0'}, set(), {'name': 'interactivename'},
     {COMRAD_PINNED_VERSION, 'tensorflow==1.0'}, 'interactivename', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, None, set(), {'name': 'interactivename'}, {COMRAD_PINNED_VERSION},
     'interactivename', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, set(), set(), {'name': 'interactivename'}, {COMRAD_PINNED_VERSION},
     'interactivename', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow'}, set(), {'name': 'interactivename', 'install_requires': [COMRAD_PINNED_VERSION, 'pytest']},
     {COMRAD_PINNED_VERSION, 'pytest'}, 'interactivename', '0.0.2', None, None, None),
    (True, {}, {'name': 'cliname', 'version': '0.0.2'}, {'tensorflow==1.0'}, set(), {'name': 'interactivename'},
     {COMRAD_PINNED_VERSION, 'tensorflow==1.0'}, 'interactivename', '0.0.2', None, None, None),
])
@mock.patch('_comrad.package.spec_builder.read_pyproject')
@mock.patch('_comrad.package.spec_builder.dump_pyproject')
@mock.patch('_comrad.package.spec_builder.confirm_spec_interactive')
@mock.patch('_comrad.package.spec_builder.scan_imports')
@mock.patch('_comrad.package.spec_builder._specialize_requirements_to_currently_installed')
def test_generate_pyproject_with_spec_succeeds(_, scan_imports, confirm_spec_interactive, dump_pyproject,
                                               read_pyproject, tmp_path: Path,
                                               force_phonebook, expected_requires, expected_name, expected_email,
                                               expected_maintainer, expected_description, expected_version,
                                               interactive, cli_other_spec_props, cli_install_requires, cached_spec,
                                               interactive_mods, scanned_requires):
    if isinstance(cached_spec, Exception) or (isinstance(cached_spec, type) and issubclass(cached_spec, Exception)):
        read_pyproject.side_effect = cached_spec
    else:
        read_pyproject.return_value = cached_spec
    scan_imports.return_value = scanned_requires

    if interactive and interactive_mods is not None:

        def modify(spec: PackageSpec, *_, **__):
            spec.update_from_dict(interactive_mods)

        confirm_spec_interactive.side_effect = modify

    entrypoint = tmp_path / 'app.ui'
    assert not entrypoint.exists()
    entrypoint.touch()

    generate_pyproject_with_spec(entrypoint=entrypoint,
                                 interactive=interactive,
                                 force_phonebook=force_phonebook,
                                 cli_other_spec_props=cli_other_spec_props,
                                 cli_install_requires=set(map(Requirement, cli_install_requires)) if cli_install_requires is not None else None)

    expected_spec = PackageSpec(name=expected_name,
                                version=expected_version,
                                entrypoint='app.ui',
                                install_requires=set(map(Requirement, expected_requires)),
                                description=expected_description,
                                maintainer=expected_maintainer,
                                maintainer_email=expected_email)

    dump_pyproject.assert_called_once_with(spec=expected_spec, project_root=tmp_path)


@pytest.mark.parametrize('entrypoint,expected_error', [
    ('app_dir', 'Specified file "app_dir" is not found'),
    ('app.ui', 'Specified file "app.ui" is not found'),
    ('app.py', 'Specified file "app.py" is not found'),
])
@pytest.mark.parametrize('interactive', [True, False])
@pytest.mark.parametrize('force_phonebook', [True, False])
@pytest.mark.parametrize('cli_other_spec_props', [None, {}, {'name': 'custom'}])
@pytest.mark.parametrize('cli_install_requires', [None, set(), {'pytest'}])
def test_generate_pyproject_with_spec_fails_when_entrypoint_missing(expected_error, entrypoint, force_phonebook,
                                                                    interactive, cli_other_spec_props,
                                                                    cli_install_requires):
    with pytest.raises(AssertionError, match=expected_error):
        _generate_pyproject_with_spec_unsafe(entrypoint=Path(entrypoint),
                                             interactive=interactive,
                                             force_phonebook=force_phonebook,
                                             cli_other_spec_props=cli_other_spec_props,
                                             cli_install_requires=(set(map(Requirement, cli_install_requires))
                                                                   if cli_install_requires is not None else None))


@pytest.mark.parametrize('interactive', [True, False])
@pytest.mark.parametrize('force_phonebook', [True, False])
@pytest.mark.parametrize('cli_other_spec_props', [None, {}, {'name': 'custom'}])
@pytest.mark.parametrize('cli_install_requires', [None, set(), {'pytest'}])
def test_generate_pyproject_with_spec_fails_when_entrypoint_is_dir(force_phonebook,
                                                                   interactive, cli_other_spec_props,
                                                                   cli_install_requires, tmp_path: Path):
    entrypoint = tmp_path / 'app_dir'
    entrypoint.mkdir()
    with pytest.raises(AssertionError, match=f'Specified file "{entrypoint!s}" is not found'):
        _generate_pyproject_with_spec_unsafe(entrypoint=entrypoint,
                                             interactive=interactive,
                                             force_phonebook=force_phonebook,
                                             cli_other_spec_props=cli_other_spec_props,
                                             cli_install_requires=(set(map(Requirement, cli_install_requires))
                                                                   if cli_install_requires is not None else None))


@pytest.mark.parametrize('entrypoint', [
    'app_dir',
    'app.ui.bak',
    'app.txt',
])
@pytest.mark.parametrize('interactive', [True, False])
@pytest.mark.parametrize('force_phonebook', [True, False])
@pytest.mark.parametrize('cli_other_spec_props', [None, {}, {'name': 'custom'}])
@pytest.mark.parametrize('cli_install_requires', [None, set(), {'pytest'}])
def test_generate_pyproject_with_spec_fails_invalid_entrypoint_extension(entrypoint, force_phonebook,
                                                                         interactive, cli_other_spec_props,
                                                                         cli_install_requires, tmp_path: Path):
    entrypoint_path = tmp_path / entrypoint
    entrypoint_path.touch()
    with pytest.raises(AssertionError, match=r'Only Python files \(\*\.py\) or Designer files \(\*\.ui\) are supported'):
        _generate_pyproject_with_spec_unsafe(entrypoint=entrypoint_path,
                                             interactive=interactive,
                                             force_phonebook=force_phonebook,
                                             cli_other_spec_props=cli_other_spec_props,
                                             cli_install_requires=(set(map(Requirement, cli_install_requires))
                                                                   if cli_install_requires is not None else None))


@pytest.mark.parametrize('entrypoint', [
    'app.py',
    'app.ui',
])
@pytest.mark.parametrize('interactive', [True, False])
@pytest.mark.parametrize('force_phonebook', [True, False])
@pytest.mark.parametrize('cli_other_spec_props', [None, {}, {'name': 'custom'}])
@pytest.mark.parametrize('cli_install_requires', [None, set(), {'pytest'}])
@mock.patch('_comrad.package.spec_builder.read_pyproject', side_effect=InvalidProjectFileError)
@mock.patch('_comrad.package.spec_builder.dump_pyproject')
@mock.patch('_comrad.package.spec_builder.PackageSpec.validate', side_effect=ValueError('Test error'))
@mock.patch('_comrad.package.spec_builder.confirm_spec_interactive')
@mock.patch('_comrad.package.spec_builder.scan_imports', return_value=set())
@mock.patch('_comrad.package.spec_builder._specialize_requirements_to_currently_installed')
def test_generate_pyproject_with_spec_fails_with_invalid_spec(_, __, ___, ____, _____, ______, entrypoint,
                                                              force_phonebook, interactive, cli_other_spec_props,
                                                              cli_install_requires, tmp_path: Path):
    entrypoint_path = tmp_path / entrypoint
    entrypoint_path.touch()
    with pytest.raises(AssertionError, match='Invalid package specification: Test error'):
        _generate_pyproject_with_spec_unsafe(entrypoint=entrypoint_path,
                                             interactive=interactive,
                                             force_phonebook=force_phonebook,
                                             cli_other_spec_props=cli_other_spec_props,
                                             cli_install_requires=(set(map(Requirement, cli_install_requires))
                                                                   if cli_install_requires is not None else None))
