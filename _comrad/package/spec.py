from dataclasses import dataclass
from pathlib import Path
from typing import Set, Dict, Any, Optional, Union, cast
from packaging.requirements import Requirement, InvalidRequirement
from packaging.version import Version, InvalidVersion
from .utils import qualified_pkg_name


@dataclass(eq=False)
class PackageSpec:
    name: str
    version: str
    entrypoint: str
    install_requires: Set[Requirement]
    description: Optional[str] = None
    maintainer: Optional[str] = None
    maintainer_email: Optional[str] = None

    def validate(self):
        if not self.name:
            raise ValueError(f'name must not be empty')
        if not self.version:
            raise ValueError(f'version must not be empty')
        if not self.entrypoint:
            raise ValueError(f'entrypoint must not be empty')
        try:
            _ = Version(self.version)
        except InvalidVersion:
            raise ValueError(f'version "{self.version}" does not follow PEP-440 format')
        try:
            _ = Requirement(f'{self.name}=={self.version}')
        except InvalidRequirement:
            raise ValueError(f'name "{self.name}" does not qualify as package name')
        for req_specifier in self.install_requires:
            if req_specifier.name == 'comrad':
                break
        else:
            raise ValueError('"comrad" requirement missing from package spec')
        entrypoint_path = Path(self.entrypoint)
        if entrypoint_path.suffix not in ['.py', '.ui']:
            raise ValueError(f'only *.py and *.ui files are allowed as entrypoints ("{self.entrypoint}" given)')
        if str(entrypoint_path.parent) != '.':
            raise ValueError('entrypoint file is expected to be inside the root directory of '
                             f'the source tree ("{self.entrypoint}" given)')

    @classmethod
    def from_dict(cls, input: Dict[str, Any]) -> 'PackageSpec':
        essential_args: Dict[str, Any] = {
            'name': input['name'],
            'version': input['version'],
            'entrypoint': input['entrypoint'],
        }
        try:
            essential_args['install_requires'] = set(map(Requirement, input['install_requires']))
        except (KeyError, InvalidRequirement):
            essential_args['install_requires'] = set()

        extra_args = input.copy()
        extra_args.pop('name', None)
        extra_args.pop('version', None)
        extra_args.pop('install_requires', None)

        res = cls(**essential_args)
        res.update_from_dict(extra_args)
        return res

    def to_dict(self) -> Dict[str, Any]:
        output: Dict[str, Any] = {
            'name': self.name,
            'version': self.version,
            'entrypoint': self.entrypoint,
            'install_requires': list(map(str, self.install_requires)),
        }
        for key, val in vars(self).items():
            if key not in output and val:
                output[key] = val

        return output

    def update_from_dict(self, input: Dict[str, Any]):
        fields = list(vars(self).keys())
        fields.remove('install_requires')
        for field_name in fields:
            try:
                val = input[field_name]
            except KeyError:
                continue
            setattr(self, field_name, val)

        def map_req(input: Union[str, Requirement]) -> Requirement:
            return input if isinstance(input, Requirement) else Requirement(input)

        try:
            val = input['install_requires']
        except KeyError:
            pass
        else:
            self.install_requires = set(map(map_req, val))

    @property
    def qualified_name(self) -> str:
        return qualified_pkg_name(self.name)

    def __eq__(self, other: object):
        # Requirement objects do not have equality, therefore we reimplement this method to compare them by strings
        if type(other) != type(self):
            return False
        other_spec = cast(PackageSpec, other)
        regular_attrs = set(vars(self).keys())
        regular_attrs.remove('install_requires')
        for attr in regular_attrs:
            if getattr(self, attr) != getattr(other_spec, attr):
                return False
        my_deps = set(map(str, self.install_requires))
        his_deps = set(map(str, other_spec.install_requires))
        return my_deps == his_deps
