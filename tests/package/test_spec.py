import pytest
from packaging.requirements import Requirement
from _comrad.package.spec import PackageSpec


@pytest.mark.parametrize('name', ['app'])
@pytest.mark.parametrize('version', ['0.0.1', '0.1.0', '0.1b5', '2.3.dev3', '2.3a.dev1', '0.1b5+46.g0f3d126.dirty', '0.1b5+46.g0f3d126'])
@pytest.mark.parametrize('comrad_req', ['comrad', 'comrad==0.1', 'comrad @ https://example.com/comrad.git#egg=comrad'])
@pytest.mark.parametrize('install_requires', [
    [],
    ['pytest'],
    ['PyQt5'],
    ['pytest==0.0.1'],
    ['pytest==0.0.1', 'accwidgets @ https://example.com/accwidgets.git#egg=accwidgets'],
])
@pytest.mark.parametrize('description', [None, '', 'test description'])
@pytest.mark.parametrize('maintainer', [None, '', 'John'])
@pytest.mark.parametrize('maintainer_email', [None, '', 'name.surname@cern.ch'])
def test_validate_succeeds(name, version, install_requires, description,
                           maintainer_email, maintainer, comrad_req):
    full_requires = install_requires + [comrad_req]
    spec = PackageSpec(name=name,
                       version=version,
                       install_requires=set(map(Requirement, full_requires)),
                       description=description,
                       maintainer=maintainer,
                       maintainer_email=maintainer_email)
    spec.validate()


@pytest.mark.parametrize('version', ['0.0.1', '0.1.0', '0.1b5', '2.3.dev3', '2.3a.dev1', '0.1b5+46.g0f3d126.dirty', '0.1b5+46.g0f3d126'])
@pytest.mark.parametrize('install_requires', [
    ['comrad'],
    ['comrad', 'pytest'],
    ['comrad', 'accwidgets==0.1b5.dev1'],
])
@pytest.mark.parametrize('description', [None, '', 'test description'])
@pytest.mark.parametrize('maintainer', [None, '', 'John'])
@pytest.mark.parametrize('maintainer_email', [None, '', 'name.surname@cern.ch'])
@pytest.mark.parametrize('broken_prop,broken_val,expected_error', [
    ('name', '', 'name must not be empty'),
    ('name', '_some_weird:name_???', r'name "_some_weird:name_\?\?\?" does not qualify as package name'),
    ('name', '==smth', 'name "==smth" does not qualify as package name'),
    ('version', '', 'version must not be empty'),
    ('version', '???', r'version "\?\?\?" does not follow PEP-440 format'),
    ('version', 'anything', 'version "anything" does not follow PEP-440 format'),
    ('install_requires', set(), '"comrad" requirement missing from package spec'),
    ('install_requires', {Requirement('pytest')}, '"comrad" requirement missing from package spec'),
    ('install_requires', {Requirement('PyQt5')}, '"comrad" requirement missing from package spec'),
    ('install_requires', {Requirement('pytest==0.0.1')}, '"comrad" requirement missing from package spec'),
    ('install_requires', {Requirement('pytest==0.0.1'), Requirement('accwidgets @ https://example.com/accwidgets.git#egg=accwidgets')}, '"comrad" requirement missing from package spec'),
])
def test_validate_fails(version, install_requires, description,
                        maintainer_email, maintainer, expected_error, broken_prop, broken_val):
    spec = PackageSpec(name='app',
                       version=version,
                       install_requires=set(map(Requirement, install_requires)),
                       description=description,
                       maintainer=maintainer,
                       maintainer_email=maintainer_email)
    setattr(spec, broken_prop, broken_val)
    with pytest.raises(ValueError, match=expected_error):
        spec.validate()


@pytest.mark.parametrize('input1,expected_name', [
    ({'name': ''}, ''),
    ({'name': 'app'}, 'app'),
    ({'name': '???'}, '???'),
])
@pytest.mark.parametrize('input2,expected_version', [
    ({'version': '0.0.1'}, '0.0.1'),
    ({'version': ''}, ''),
    ({'version': '???'}, '???'),
])
@pytest.mark.parametrize('input3,expected_install_requires', [
    ({'install_requires': []}, set()),
    ({'install_requires': ['pydm']}, {'pydm'}),
    ({'install_requires': ['pydm', 'accwidgets==0.0.1']}, {'pydm', 'accwidgets==0.0.1'}),
    ({'install_requires': ['====notapackage-====']}, set()),
])
@pytest.mark.parametrize('input4,expected_maintainer', [
    ({'maintainer': None}, None),
    ({'maintainer': ''}, ''),
    ({'maintainer': 'Name Surname'}, 'Name Surname'),
])
@pytest.mark.parametrize('input5,expected_email', [
    ({'maintainer_email': None}, None),
    ({'maintainer_email': ''}, ''),
    ({'maintainer_email': 'name.surname@cern.ch'}, 'name.surname@cern.ch'),
])
@pytest.mark.parametrize('input6,expected_description', [
    ({'description': None}, None),
    ({'description': ''}, ''),
    ({'description': 'Test description'}, 'Test description'),
])
def test_from_dict_succeeds(input1, input2, input3, input4, input5, input6, expected_name, expected_version,
                            expected_install_requires, expected_maintainer, expected_email, expected_description):
    spec = PackageSpec.from_dict({**input1, **input2, **input3, **input4, **input5, **input6})
    assert spec.name == expected_name
    assert spec.version == expected_version
    assert set(map(str, spec.install_requires)) == set(map(str, map(Requirement, expected_install_requires)))
    assert spec.maintainer == expected_maintainer
    assert spec.maintainer_email == expected_email
    assert spec.description == expected_description


@pytest.mark.parametrize('maintainer', [None, '', 'Name Surname'])
@pytest.mark.parametrize('email', [None, '', 'name.surname@cern.ch'])
@pytest.mark.parametrize('description', [None, '', 'Test description'])
@pytest.mark.parametrize('input,error_type', [
    ({'name': 'app', 'install_requires': []}, KeyError),
    ({'version': '0.0.1', 'install_requires': []}, KeyError),
    ({}, KeyError),
    ({'name': 'app', 'version': '0.0.1', 'install_requires': 34}, TypeError),
])
def test_from_dict_fails(maintainer, email, description, input, error_type):
    with pytest.raises(error_type):
        PackageSpec.from_dict({
            'maintainer': maintainer,
            'maintainer_email': email,
            'description': description,
            **input,
        })


@pytest.mark.parametrize('name,version,install_requires,maintainer,email,description,expected_dict', [
    ('app', '0.0.1', [], None, None, None, {'name': 'app', 'version': '0.0.1', 'install_requires': []}),
    ('', '0.0.1', [], None, None, None, {'name': '', 'version': '0.0.1', 'install_requires': []}),
    ('app', '', [], None, None, None, {'name': 'app', 'version': '', 'install_requires': []}),
    ('app', '0.0.1', ['pydm'], None, None, None, {'name': 'app', 'version': '0.0.1', 'install_requires': ['pydm']}),
    ('', '0.0.1', ['pydm'], None, None, None, {'name': '', 'version': '0.0.1', 'install_requires': ['pydm']}),
    ('app', '', ['pydm'], None, None, None, {'name': 'app', 'version': '', 'install_requires': ['pydm']}),
    ('app', '0.0.1', [], None, 'name.surname@cern.ch', None, {'name': 'app', 'version': '0.0.1', 'install_requires': [], 'maintainer_email': 'name.surname@cern.ch'}),
    ('', '0.0.1', [], None, 'name.surname@cern.ch', None, {'name': '', 'version': '0.0.1', 'install_requires': [], 'maintainer_email': 'name.surname@cern.ch'}),
    ('app', '', [], None, 'name.surname@cern.ch', None, {'name': 'app', 'version': '', 'install_requires': [], 'maintainer_email': 'name.surname@cern.ch'}),
    ('app', '0.0.1', ['pydm'], None, 'name.surname@cern.ch', None, {'name': 'app', 'version': '0.0.1', 'install_requires': ['pydm'], 'maintainer_email': 'name.surname@cern.ch'}),
    ('', '0.0.1', ['pydm'], None, 'name.surname@cern.ch', None, {'name': '', 'version': '0.0.1', 'install_requires': ['pydm'], 'maintainer_email': 'name.surname@cern.ch'}),
    ('app', '', ['pydm'], None, 'name.surname@cern.ch', None, {'name': 'app', 'version': '', 'install_requires': ['pydm'], 'maintainer_email': 'name.surname@cern.ch'}),
    ('app', '0.0.1', [], 'Name Surname', None, None, {'name': 'app', 'version': '0.0.1', 'install_requires': [], 'maintainer': 'Name Surname'}),
    ('', '0.0.1', [], 'Name Surname', None, None, {'name': '', 'version': '0.0.1', 'install_requires': [], 'maintainer': 'Name Surname'}),
    ('app', '', [], 'Name Surname', None, None, {'name': 'app', 'version': '', 'install_requires': [], 'maintainer': 'Name Surname'}),
    ('app', '0.0.1', ['pydm'], 'Name Surname', None, None, {'name': 'app', 'version': '0.0.1', 'install_requires': ['pydm'], 'maintainer': 'Name Surname'}),
    ('', '0.0.1', ['pydm'], 'Name Surname', None, None, {'name': '', 'version': '0.0.1', 'install_requires': ['pydm'], 'maintainer': 'Name Surname'}),
    ('app', '', ['pydm'], 'Name Surname', None, None, {'name': 'app', 'version': '', 'install_requires': ['pydm'], 'maintainer': 'Name Surname'}),
    ('app', '0.0.1', [], 'Name Surname', 'name.surname@cern.ch', None, {'name': 'app', 'version': '0.0.1', 'install_requires': [], 'maintainer': 'Name Surname', 'maintainer_email': 'name.surname@cern.ch'}),
    ('', '0.0.1', [], 'Name Surname', 'name.surname@cern.ch', None, {'name': '', 'version': '0.0.1', 'install_requires': [], 'maintainer': 'Name Surname', 'maintainer_email': 'name.surname@cern.ch'}),
    ('app', '', [], 'Name Surname', 'name.surname@cern.ch', None, {'name': 'app', 'version': '', 'install_requires': [], 'maintainer': 'Name Surname', 'maintainer_email': 'name.surname@cern.ch'}),
    ('app', '0.0.1', ['pydm'], 'Name Surname', 'name.surname@cern.ch', None, {'name': 'app', 'version': '0.0.1', 'install_requires': ['pydm'], 'maintainer': 'Name Surname', 'maintainer_email': 'name.surname@cern.ch'}),
    ('', '0.0.1', ['pydm'], 'Name Surname', 'name.surname@cern.ch', None, {'name': '', 'version': '0.0.1', 'install_requires': ['pydm'], 'maintainer': 'Name Surname', 'maintainer_email': 'name.surname@cern.ch'}),
    ('app', '', ['pydm'], 'Name Surname', 'name.surname@cern.ch', None, {'name': 'app', 'version': '', 'install_requires': ['pydm'], 'maintainer': 'Name Surname', 'maintainer_email': 'name.surname@cern.ch'}),
    ('app', '0.0.1', [], None, None, '', {'name': 'app', 'version': '0.0.1', 'install_requires': []}),
    ('', '0.0.1', [], None, None, '', {'name': '', 'version': '0.0.1', 'install_requires': []}),
    ('app', '', [], None, None, '', {'name': 'app', 'version': '', 'install_requires': []}),
    ('app', '0.0.1', ['pydm'], None, None, '', {'name': 'app', 'version': '0.0.1', 'install_requires': ['pydm']}),
    ('', '0.0.1', ['pydm'], None, None, '', {'name': '', 'version': '0.0.1', 'install_requires': ['pydm']}),
    ('app', '', ['pydm'], None, None, '', {'name': 'app', 'version': '', 'install_requires': ['pydm']}),
    ('app', '0.0.1', [], None, '', None, {'name': 'app', 'version': '0.0.1', 'install_requires': []}),
    ('', '0.0.1', [], None, '', None, {'name': '', 'version': '0.0.1', 'install_requires': []}),
    ('app', '', [], None, '', None, {'name': 'app', 'version': '', 'install_requires': []}),
    ('app', '0.0.1', ['pydm'], None, '', None, {'name': 'app', 'version': '0.0.1', 'install_requires': ['pydm']}),
    ('', '0.0.1', ['pydm'], None, '', None, {'name': '', 'version': '0.0.1', 'install_requires': ['pydm']}),
    ('app', '', ['pydm'], None, '', None, {'name': 'app', 'version': '', 'install_requires': ['pydm']}),
    ('app', '0.0.1', [], '', None, None, {'name': 'app', 'version': '0.0.1', 'install_requires': []}),
    ('', '0.0.1', [], '', None, None, {'name': '', 'version': '0.0.1', 'install_requires': []}),
    ('app', '', [], '', None, None, {'name': 'app', 'version': '', 'install_requires': []}),
    ('app', '0.0.1', ['pydm'], '', None, None, {'name': 'app', 'version': '0.0.1', 'install_requires': ['pydm']}),
    ('', '0.0.1', ['pydm'], '', None, None, {'name': '', 'version': '0.0.1', 'install_requires': ['pydm']}),
    ('app', '', ['pydm'], '', None, None, {'name': 'app', 'version': '', 'install_requires': ['pydm']}),
    ('app', '0.0.1', [], None, None, 'Text', {'name': 'app', 'version': '0.0.1', 'install_requires': [], 'description': 'Text'}),
    ('', '0.0.1', [], None, None, 'Text', {'name': '', 'version': '0.0.1', 'install_requires': [], 'description': 'Text'}),
    ('app', '', [], None, None, 'Text', {'name': 'app', 'version': '', 'install_requires': [], 'description': 'Text'}),
    ('app', '0.0.1', ['pydm'], None, None, 'Text', {'name': 'app', 'version': '0.0.1', 'install_requires': ['pydm'], 'description': 'Text'}),
    ('', '0.0.1', ['pydm'], None, None, 'Text', {'name': '', 'version': '0.0.1', 'install_requires': ['pydm'], 'description': 'Text'}),
    ('app', '', ['pydm'], None, None, 'Text', {'name': 'app', 'version': '', 'install_requires': ['pydm'], 'description': 'Text'}),
])
def test_to_dict(name, version, install_requires, maintainer, email, description, expected_dict):
    spec = PackageSpec(name=name,
                       version=version,
                       install_requires=set(map(Requirement, install_requires)),
                       description=description,
                       maintainer=maintainer,
                       maintainer_email=email)
    assert spec.to_dict() == expected_dict


@pytest.mark.parametrize('old_name,new_name', [
    ('app', ''),
    ('', 'app'),
    ('app', 'app2'),
])
@pytest.mark.parametrize('old_version,new_version', [
    ('0.0.1', '0.1.0'),
    ('0.1b5', '2.3.dev3'),
    ('2.3a.dev1', '0.1b5+46.g0f3d126.dirty'),
    ('0.1b5+46.g0f3d126', ''),
])
@pytest.mark.parametrize('old_reqs,new_reqs', [
    ([], ['pytest']),
    (['PyQt5'], ['PyQt5==0.0.1']),
])
@pytest.mark.parametrize('old_description,new_description', [
    (None, ''),
    ('', None),
    (None, 'test description'),
    ('', ''),
])
@pytest.mark.parametrize('old_maintainer,new_maintainer', [
    (None, ''),
    ('', None),
    (None, 'John'),
    ('', ''),
])
@pytest.mark.parametrize('old_email,new_email', [
    (None, ''),
    ('', None),
    (None, 'name.surname@cern.ch'),
    ('', ''),
])
def test_update(old_description, old_email, old_maintainer, old_name, old_reqs, old_version, new_description,
                new_email, new_maintainer, new_name, new_reqs, new_version):
    spec1 = PackageSpec(name=old_name,
                        version=old_version,
                        install_requires=set(map(Requirement, old_reqs)),
                        description=old_description,
                        maintainer=old_maintainer,
                        maintainer_email=old_email)
    spec2 = PackageSpec(name=new_name,
                        version=new_version,
                        install_requires=set(map(Requirement, new_reqs)),
                        description=new_description,
                        maintainer=new_maintainer,
                        maintainer_email=new_email)
    spec1.update(spec2)
    assert spec1.name == new_name
    assert spec1.version == new_version
    assert set(map(str, spec1.install_requires)) == set(map(str, map(Requirement, new_reqs)))
    assert spec1.maintainer == new_maintainer
    assert spec1.maintainer_email == new_email
    assert spec1.description == new_description


def test_update_with_additional_attr_does_not_fail():
    spec1 = PackageSpec(name='app',
                        version='0.0.1',
                        install_requires=set())
    spec1.not_existing_prop = 'test'
    spec2 = PackageSpec(name='app2',
                        version='0.0.1',
                        install_requires=set(),
                        maintainer='Name')
    assert not hasattr(spec2, 'not_existing_prop')
    spec1.update(spec2)
    assert spec1.name == 'app2'
    assert spec1.version == '0.0.1'
    assert spec1.install_requires == set()
    assert spec1.maintainer == 'Name'
    assert spec1.not_existing_prop == 'test'


@pytest.mark.parametrize('input,expected_name,expected_version,expected_install_requires,expected_maintainer,expected_email,expected_description', [
    ({'install_requires': [Requirement('pydm')]}, 'app', '0.0.1', ['pydm'], None, None, None),
    ({'install_requires': ['pydm']}, 'app', '0.0.1', ['pydm'], None, None, None),
    ({'name': 'new_name'}, 'new_name', '0.0.1', [], None, None, None),
    ({'name': 'new_name', 'version': '0.0.2'}, 'new_name', '0.0.2', [], None, None, None),
    ({'version': '0.0.2'}, 'app', '0.0.2', [], None, None, None),
    ({'install_requires': ['pydm'], 'maintainer': 'John Smith'}, 'app', '0.0.1', ['pydm'], 'John Smith', None, None),
    ({'install_requires': ['pydm'], 'maintainer_email': 'John.Smith@cern.ch'}, 'app', '0.0.1', ['pydm'], None, 'John.Smith@cern.ch', None),
    ({'install_requires': ['pydm'], 'description': 'Text'}, 'app', '0.0.1', ['pydm'], None, None, 'Text'),
    ({'install_requires': ['pydm'], 'maintainer': 'John Smith', 'maintainer_email': 'John.Smith@cern.ch', 'description': 'Text'}, 'app', '0.0.1', ['pydm'], 'John Smith', 'John.Smith@cern.ch', 'Text'),
    ({'garbage_key': 'something'}, 'app', '0.0.1', [], None, None, None),
    ({}, 'app', '0.0.1', [], None, None, None),
])
def test_update_from_dict(input, expected_description, expected_email, expected_maintainer, expected_install_requires,
                          expected_version, expected_name):
    spec = PackageSpec(name='app',
                       version='0.0.1',
                       install_requires=set())
    spec.update_from_dict(input)
    assert spec.name == expected_name
    assert spec.version == expected_version
    assert set(map(str, spec.install_requires)) == set(map(str, map(Requirement, expected_install_requires)))
    assert spec.maintainer == expected_maintainer
    assert spec.maintainer_email == expected_email
    assert spec.description == expected_description


@pytest.mark.parametrize('name1,name2,name_equal', [
    ('', '', True),
    ('app', '', False),
    ('app', 'app', True),
    ('app1', 'app2', False),
])
@pytest.mark.parametrize('ver1,ver2,ver_equal', [
    ('', '', True),
    ('0.0.1', '', False),
    ('0.0.1', '0.0.1', True),
    ('0.0.1', '0.0.1a1', False),
])
@pytest.mark.parametrize('deps1,deps2,deps_equal', [
    (set(), set(), True),
    ({'pkg1'}, {'pkg2'}, False),
    ({'pkg1'}, {'pkg1==0.1'}, False),
    ({'pkg1'}, set(), False),
    ({'pkg1'}, {'pkg1', 'pkg2'}, False),
])
@pytest.mark.parametrize('desc1,desc2,desc_equal', [
    (None, None, True),
    ('', None, False),
    ('Text', '', False),
    (None, 'Text', False),
])
@pytest.mark.parametrize('maintainer1,maintainer2,maintainer_equal', [
    (None, None, True),
    (None, '', False),
    ('John', '', False),
    ('John', 'John', True),
])
@pytest.mark.parametrize('email1,email2,email_equal', [
    (None, None, True),
    (None, '', False),
    ('John@example.com', '', False),
    ('John@example.com', 'John@example.com', True),
])
def test_equality(name1, name2, ver1, ver2, deps1, deps2, desc1, desc2, maintainer1, maintainer2, email1, email2,
                  name_equal, ver_equal, deps_equal, desc_equal, maintainer_equal, email_equal):
    should_equal = name_equal and ver_equal and deps_equal and desc_equal and maintainer_equal and email_equal
    spec1 = PackageSpec(name=name1,
                        version=ver1,
                        install_requires=set(map(Requirement, deps1)),
                        description=desc1,
                        maintainer=maintainer1,
                        maintainer_email=email1)
    spec2 = PackageSpec(name=name2,
                        version=ver2,
                        install_requires=set(map(Requirement, deps2)),
                        description=desc2,
                        maintainer=maintainer2,
                        maintainer_email=email2)
    assert (spec1 == spec2) == should_equal
