# Implementation of reading PEP-518 pyproject.toml, while keeping common metadata (when possible) by
# PEP-621 conventions.

import logging
import toml
from toml import TomlDecodeError
from typing import Dict, Any, cast
from pathlib import Path
from _comrad.comrad_info import COMRAD_VERSION
from .spec import PackageSpec


logger = logging.getLogger(__name__)


def get_last_installable_version() -> str:
    version = COMRAD_VERSION.split('+')[0]
    return f'comrad=={version}'


COMRAD_PINNED_VERSION = get_last_installable_version()


class InvalidProjectFileError(Exception):
    pass


def read_pyproject(project_root: Path) -> Dict[str, Any]:
    project_file = project_root / _FILENAME
    logger.debug(f'Attempting to get spec from {project_file!s}')
    try:
        with project_file.open('r') as f:
            try:
                return cast(Dict[str, Any], toml.load(f))
            except (ValueError, TomlDecodeError) as e:
                raise InvalidProjectFileError(e) from e
    except FileNotFoundError as e:
        raise InvalidProjectFileError(e) from e


def dump_pyproject(spec: PackageSpec, project_root: Path) -> Path:
    project_file = project_root / _FILENAME
    contents = _spec_to_pyproject_dict(spec)
    logger.debug(f'Writing spec into {project_file!s}')
    with project_file.open('w') as f:
        toml.dump(contents, f)
    return project_file


def pyproject_dict_to_spec_dict(pyproject_dict: Dict[str, Any]) -> Dict[str, Any]:
    spec_dict = pyproject_dict[_TOML_TOOL_KEY]['comrad']['package']
    spec_dict['name'] = pyproject_dict[_TOML_PROJ_KEY]['name']
    spec_dict['version'] = pyproject_dict[_TOML_PROJ_KEY]['version']
    spec_dict['install_requires'] = pyproject_dict[_TOML_PROJ_KEY]['dependencies']

    def inject_optional(container: Dict[str, Any], src_key: str, dest_key: str):
        val = container.get(src_key, None)
        if val is not None:
            spec_dict[dest_key] = val

    inject_optional(container=pyproject_dict[_TOML_PROJ_KEY], src_key='description', dest_key='description')
    try:
        maintainer = pyproject_dict[_TOML_PROJ_KEY].get('maintainers', [])[0]
    except IndexError:
        pass
    else:
        inject_optional(container=maintainer, src_key='name', dest_key='maintainer')
        inject_optional(container=maintainer, src_key='email', dest_key='maintainer_email')
    return spec_dict


def _spec_to_pyproject_dict(spec: PackageSpec):
    spec_dict = spec.to_dict()
    maintainer = spec_dict.pop('maintainer', None)
    maintainer_email = spec_dict.pop('maintainer_email', None)
    additional_dict = {}
    if maintainer is not None or maintainer_email is not None:
        additional_dict['maintainers'] = [{
            'name': maintainer,
            'email': maintainer_email,
        }]
    contents = {
        _TOML_PROJ_KEY: {  # Follows PEP-621 paradigm
            'name': spec_dict.pop('name'),
            'version': spec_dict.pop('version'),
            'dependencies': spec_dict.pop('install_requires'),
            'description': spec_dict.pop('description', None),
            **additional_dict,
        },
        'build-system': {
            'requires': [
                COMRAD_PINNED_VERSION,
            ],
            'build-backend': 'comrad_package.builder',
        },
    }
    if spec_dict:
        # If any extra fields are remaining
        contents[_TOML_TOOL_KEY] = {
            'comrad': {
                'package': spec_dict,
            },
        }
    return contents


_FILENAME = 'pyproject.toml'
_TOML_TOOL_KEY = 'tool'
_TOML_PROJ_KEY = 'project'
