import pytest
from pathlib import Path
from unittest import mock
from packaging.requirements import Requirement
from _comrad.package.pyproject import (pyproject_dict_to_spec_dict, _spec_to_pyproject_dict, PackageSpec,
                                       COMRAD_PINNED_VERSION, read_pyproject, InvalidProjectFileError, dump_pyproject,
                                       get_last_installable_version)


@pytest.mark.parametrize('input,expected_dict', [
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1']}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app2', 'version': '0.0.2', 'dependencies': ['comrad==0.1', 'pytest<3.5']}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app2', 'version': '0.0.2', 'install_requires': ['comrad==0.1', 'pytest<3.5'], 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'description': 'Text', 'dependencies': ['comrad==0.1']}, 'tool': {'comrad': {'package': {'entrypoint': 'app.py'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'description': 'Text', 'entrypoint': 'app.py'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'description': '', 'dependencies': ['comrad==0.1']}, 'tool': {'comrad': {'package': {'entrypoint': 'app.py'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'description': '', 'entrypoint': 'app.py'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': []}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': [{}]}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': [{'email': 'one@domain.com'}]}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'maintainer_email': 'one@domain.com', 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': [{'email': 'one@domain.com'}, {'email': 'two@domain.com'}]}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'maintainer_email': 'one@domain.com', 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': [{'name': 'John Smith'}]}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'maintainer': 'John Smith', 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': [{'name': 'John Smith', 'email': 'john.smith@domain.com'}]}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'maintainer': 'John Smith', 'maintainer_email': 'john.smith@domain.com', 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': [{'name': 'John Smith', 'email': 'john.smith@domain.com'},
                                                                                                      {'name': 'maintainer2', 'email': 'two@domain.com'}]}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'maintainer': 'John Smith', 'maintainer_email': 'john.smith@domain.com', 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app', 'version': '0.0.1', 'description': 'Text', 'dependencies': ['comrad==0.1'], 'maintainers': [{'name': 'John Smith', 'email': 'john.smith@domain.com'}]},
      'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'description': 'Text', 'maintainer': 'John Smith', 'maintainer_email': 'john.smith@domain.com', 'entrypoint': 'app.ui'}),
    ({'project': {'not-related': 'test', 'requires-python': '3.8', 'name': 'app', 'version': '0.0.1', 'description': 'Text', 'dependencies': ['comrad==0.1'],
                  'maintainers': [{'name': 'John Smith', 'email': 'john.smith@domain.com'}]}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}},
     {'name': 'app', 'version': '0.0.1', 'install_requires': ['comrad==0.1'], 'description': 'Text', 'maintainer': 'John Smith', 'maintainer_email': 'john.smith@domain.com', 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app2', 'version': '0.0.2', 'dependencies': ['comrad==0.1', 'pytest<3.5']}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui', 'name': 'another name'}}}},
     {'name': 'app2', 'version': '0.0.2', 'install_requires': ['comrad==0.1', 'pytest<3.5'], 'entrypoint': 'app.ui'}),
    ({'project': {'name': 'app2', 'version': '0.0.2', 'dependencies': ['comrad==0.1', 'pytest<3.5']}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui', 'version': 'another version'}}}},
     {'name': 'app2', 'version': '0.0.2', 'install_requires': ['comrad==0.1', 'pytest<3.5'], 'entrypoint': 'app.ui'}),
])
@pytest.mark.parametrize('build_system_input', [
    {},
    {'build-system': {}},
    {'build-system': {'requires': ['comrad==0.1'], 'build-backend': 'comrad_package.builder'}},
    {'tool': {'poetry': {'something-poetry': 'something-else'}}},
    {'tool': {'comrad': {'something-else': {'something-else': 'something-else'}}}},
])
def test_pyproject_dict_to_spec_dict_succeeds(input, expected_dict, build_system_input):
    spec_dict = pyproject_dict_to_spec_dict({**build_system_input, **input})
    assert spec_dict == expected_dict


@pytest.mark.parametrize('input,expected_error', [
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1']}, 'tool.comrad.package': {'entrypoint': 'app.ui'}}, "'tool'"),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1']}, 'tool': {'comrad': {}}}, "'package'"),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1']}, 'tool': {}}, "'comrad'"),
    ({'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1']}}, "'tool'"),
    ({'project': {'name': 'app', 'version': '0.0.1'}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}, "'dependencies'"),
    ({'project': {'name': 'app', 'dependencies': ['comrad==0.1']}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}, "'version'"),
    ({'project': {'version': '0.0.1', 'dependencies': ['comrad==0.1']}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}, "'name'"),
    ({'project': {}, 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}, "'name'"),
    ({'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}, "'project'"),
    ({}, "'tool'"),
])
@pytest.mark.parametrize('optional_input', [
    {},
    {'description': 'Text'},
    {'maintainers': [{}]},
    {'maintainers': [{'name': 'John Smith'}]},
    {'maintainers': [{'email': 'John.Smith@domain.com'}]},
    {'maintainers': [{'name': 'John Smith', 'email': 'John.Smith@domain.com'}]},
    {'maintainers': [{'email': 'John.Smith@domain.com'}, {'name': 'Another one'}]},
    {'description': 'Text', 'maintainers': [{}]},
])
@pytest.mark.parametrize('build_system_input', [
    {},
    {'build-system': {}},
    {'build-system': {'requires': ['comrad==0.1'], 'build-backend': 'comrad_package.builder'}},
])
def test_pyproject_dict_to_spec_dict_fails(input, expected_error, build_system_input, optional_input):
    combined_dict = {**build_system_input, **optional_input, **input}
    with pytest.raises(KeyError, match=expected_error):
        pyproject_dict_to_spec_dict(combined_dict)


@pytest.mark.parametrize('name,version,entrypoint,install_requires,description,maintainer,email,expected_dict', [
    ('app', '0.0.1', 'app.ui', ['comrad==0.1'], None, None, None, {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'description': None},
                                                                   'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                   'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app', '0.0.1', 'app.ui', ['comrad==0.1', 'pytest<3.5'], None, None, None, {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1', 'pytest<3.5'], 'description': None},
                                                                                 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                                 'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app2', '0.0.2', 'app.ui', ['comrad==0.1'], None, None, None, {'project': {'name': 'app2', 'version': '0.0.2', 'dependencies': ['comrad==0.1'], 'description': None},
                                                                    'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                    'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app', '0.0.1', 'app.ui', ['comrad==0.1'], 'Text', None, None, {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'description': 'Text'},
                                                                     'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                     'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app', '0.0.1', 'app.ui', ['comrad==0.1'], '', None, None, {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'description': None},
                                                                 'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                 'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app', '0.0.1', 'app.ui', ['comrad==0.1'], None, 'John Smith', None, {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': [{'name': 'John Smith', 'email': None}], 'description': None},
                                                                           'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                           'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app', '0.0.1', 'app.ui', ['comrad==0.1'], None, None, 'John.Smith@domain.com', {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'],
                                                                                                  'maintainers': [{'email': 'John.Smith@domain.com', 'name': None}], 'description': None},
                                                                                      'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                                      'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app', '0.0.1', 'app.ui', ['comrad==0.1'], None, 'John Smith', 'John.Smith@domain.com', {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'],
                                                                                                          'maintainers': [{'name': 'John Smith', 'email': 'John.Smith@domain.com'}], 'description': None},
                                                                                              'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                                              'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app', '0.0.1', 'app.ui', ['comrad==0.1'], 'Text', 'John Smith', 'John.Smith@domain.com', {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'],
                                                                                                            'maintainers': [{'name': 'John Smith', 'email': 'John.Smith@domain.com'}], 'description': 'Text'},
                                                                                                'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                                                'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
    ('app', '0.0.1', 'app.ui', ['comrad==0.1'], 'Text', None, 'John.Smith@domain.com', {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'],
                                                                                                    'maintainers': [{'name': None, 'email': 'John.Smith@domain.com'}], 'description': 'Text'},
                                                                                        'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}},
                                                                                        'build-system': {'build-backend': 'comrad_package.builder', 'requires': [COMRAD_PINNED_VERSION]}}),
])
def test_spec_to_pyproject_dict(name, version, install_requires, description, maintainer, email, entrypoint, expected_dict):
    spec = PackageSpec(name=name,
                       version=version,
                       entrypoint=entrypoint,
                       install_requires=set(map(Requirement, install_requires)),
                       description=description,
                       maintainer=maintainer,
                       maintainer_email=email)
    actual_dict = _spec_to_pyproject_dict(spec)
    # Allow some flexibility because set translated to list does not preserve deterministic order
    actual_dict['project']['dependencies'].sort()
    assert actual_dict == expected_dict


@pytest.mark.parametrize('contents,expected_dict', [
    ('', {}),
    ("""
[project]""", {'project': {}}),
    ("""
[project]
name = "test"
version = "0.0.1"
""", {'project': {'name': 'test', 'version': '0.0.1'}}),
    ("""
[project]
name = "app"
version = "0.0.1"
dependencies = [ "comrad==0.1",]
[[project.maintainers]]
name = "John Smith"
email = "John.Smith@domain.com"
""", {'project': {'name': 'app', 'version': '0.0.1', 'dependencies': ['comrad==0.1'], 'maintainers': [{'name': 'John Smith', 'email': 'John.Smith@domain.com'}]}}),
    ("""
[build-system]
requires = [ "comrad==0.1",]
build-backend = "comrad_package.builder"
""", {'build-system': {'requires': ['comrad==0.1'], 'build-backend': 'comrad_package.builder'}}),
    ("""
[tool.comrad.package]
entrypoint = "app.ui"
""", {'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}),
    ("""
[project]
name = "example"
version = "0.0.2"
dependencies = [ "pytest",]
[[project.maintainers]]
name = "John Smith"

[build-system]
requires = [ "comrad==2.0",]
build-backend = "comrad_package.builder"

[tool.comrad.package]
entrypoint = "app.ui"
""", {'project': {'name': 'example', 'version': '0.0.2', 'dependencies': ['pytest'], 'maintainers': [{'name': 'John Smith'}]},
      'build-system': {'requires': ['comrad==2.0'], 'build-backend': 'comrad_package.builder'},
      'tool': {'comrad': {'package': {'entrypoint': 'app.ui'}}}}),
])
def test_read_pyproject_succeeds(tmp_path: Path, contents, expected_dict):
    project_file = tmp_path / 'pyproject.toml'
    project_file.write_text(contents)
    res = read_pyproject(project_root=tmp_path)
    assert res == expected_dict


def test_read_pyproject_fails_to_find_file(tmp_path: Path):
    with pytest.raises(InvalidProjectFileError, match='test'):
        read_pyproject(project_root=tmp_path)


@pytest.mark.parametrize('contents,expected_error', [
    ('[project', 'Key group not on a line by itself*'),
    ('[project][project]', 'Key group not on a line by itself*'),
    ("""[project]
[project]""", r'What\? project already exists\?*'),
    ("""[tool.comrad.package]
[tool.comrad.package]""", r'What\? package already exists\?*'),
    ("""[project]
name = "test"
[project]
name = "test"
""", r'What\? project already exists\?*'),
])
def test_read_pyproject_fails_to_parse_toml(tmp_path: Path, expected_error, contents):
    project_file = tmp_path / 'pyproject.toml'
    project_file.write_text(contents)
    with pytest.raises(InvalidProjectFileError, match=expected_error):
        read_pyproject(project_root=tmp_path)


@pytest.mark.parametrize('name', ['', 'app'])
@pytest.mark.parametrize('version', ['', '0.0.1'])
@pytest.mark.parametrize('entrypoint', ['', 'app.ui', 'main.py'])
@pytest.mark.parametrize('install_requires', [[], ['pydm']])
@pytest.mark.parametrize('maintainer', [None, '', 'Name Surname'])
@pytest.mark.parametrize('email', [None, '', 'name.surname@domain.com'])
@pytest.mark.parametrize('description', [None, '', 'Text'])
@pytest.mark.parametrize('file_exists', [True, False])
@mock.patch('_comrad.package.pyproject.toml.dump')
def test_dump_pyproject(dump, tmp_path: Path, file_exists, name, version, entrypoint, install_requires, maintainer, email,
                        description):
    project_file = tmp_path / 'pyproject.toml'
    assert not project_file.exists()
    if file_exists:
        project_file.write_text('[project]\nname = "something"')

    def toml_dump_side_effect(_, file):
        file.write('test')

    dump.side_effect = toml_dump_side_effect

    spec = PackageSpec(name=name,
                       version=version,
                       entrypoint=entrypoint,
                       install_requires=set(map(Requirement, install_requires)),
                       description=description,
                       maintainer=maintainer,
                       maintainer_email=email)
    expected_contents = _spec_to_pyproject_dict(spec)
    dump_pyproject(spec=spec, project_root=tmp_path)
    assert project_file.exists()
    dump.assert_called_once_with(expected_contents, mock.ANY)


@pytest.mark.parametrize('version,expected_result', [
    ('0.1b5', 'comrad==0.1b5'),
    ('0.1b5+0.g9c93510.dirty', 'comrad==0.1b5'),
    ('0.1b4+42.gc3f7692', 'comrad==0.1b4'),
])
def test_get_last_installable_version(version, expected_result, monkeypatch):
    from _comrad.package import pyproject
    monkeypatch.setattr(pyproject, 'COMRAD_VERSION', version)
    assert get_last_installable_version() == expected_result
