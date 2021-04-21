import logging
import sys
import functools
import subprocess
import operator
from pathlib import Path
from typing import Dict, Optional, Set, Any
from packaging.requirements import Requirement, InvalidRequirement
from .importlib_shim import find_distribution_name, importlib_metadata
from .spec import PackageSpec
from .pyproject import read_pyproject, dump_pyproject, InvalidProjectFileError, COMRAD_PINNED_VERSION, pyproject_dict_to_spec_dict
from .import_scanning import scan_imports
from .wizard import confirm_spec_interactive


logger = logging.getLogger(__name__)


def make_requirement_safe(input: str, error: str) -> Optional[Requirement]:
    # Not only create a requirement object, but provide a real package name (if can be found) via
    # importlib_metadata, e.g.
    # qtpy -> QtPy
    # jpype -> JPype1
    dist_name = find_distribution_name(input)
    if dist_name:
        input = dist_name
    try:
        return Requirement(input)
    except InvalidRequirement:
        logger.warning(f'Cannot parse requirement "{input}". {error}')
        return None


def generate_pyproject_with_spec(entrypoint: Path,
                                 interactive: bool,
                                 force_phonebook: bool,
                                 cli_other_spec_props: Optional[Dict[str, Any]] = None,
                                 cli_install_requires: Optional[Set[Requirement]] = None):
    """
    Creates a proposed specification of the package to build and saves it in PEP-517 compatible pyproject.toml
    in the same directory, as the ``entrypoint`` file.

    Args:
        entrypoint: Path to the entrypoint file of the ComRAD application. This has to be either *.py or *.ui file.
        interactive: Whether create a spec in interactive mode. When :obj:`True`, the user will be asked questions and
                     given choices.
        force_phonebook: Enforce resolution of the maintainer info from phonebook, disregarding cache.
        cli_install_requires: Initial set of requirements that can be supplied via CLI arguments.
        cli_other_spec_props: High-priority overloads that can override any properties of the default spec. This is
                              expected to come from the CLI arguments.
    """
    try:
        _generate_pyproject_with_spec_unsafe(entrypoint=entrypoint,
                                             interactive=interactive,
                                             force_phonebook=force_phonebook,
                                             cli_install_requires=cli_install_requires,
                                             cli_other_spec_props=cli_other_spec_props)
    except AssertionError as e:
        logger.error(str(e))
        exit(1)


def _generate_pyproject_with_spec_unsafe(entrypoint: Path,
                                         interactive: bool,
                                         force_phonebook: bool,
                                         cli_other_spec_props: Optional[Dict[str, Any]] = None,
                                         cli_install_requires: Optional[Set[Requirement]] = None):
    assert entrypoint.exists() and entrypoint.is_file(), f'Specified file "{entrypoint!s}" is not found'
    assert entrypoint.suffix in ['.ui', '.py'], 'Only Python files (*.py) or Designer files (*.ui) are supported'
    default_spec = PackageSpec(name=entrypoint.stem,
                               version='0.0.1',
                               entrypoint=entrypoint.name,
                               install_requires=set())
    final_spec = default_spec

    cached_spec_dict: Optional[Dict[str, Any]]
    try:
        pyproject_dict = read_pyproject(project_root=entrypoint.parent)
    except InvalidProjectFileError as e:
        logger.debug(f'Could not retrieve pyproject.toml cache: {e!s}')
        cached_spec_dict = None
    else:
        try:
            cached_spec_dict = pyproject_dict_to_spec_dict(pyproject_dict)
        except KeyError as e:
            logger.debug(f'Could not retrieve pyproject.toml cache: Key error - {e!s}')
            cached_spec_dict = None

    if cached_spec_dict is not None:
        final_spec.update_from_dict(cached_spec_dict)
        final_spec.entrypoint = entrypoint.name

    if cli_other_spec_props:
        # Update with "higher-priority" settings (e.g. coming from CLI args)
        final_spec.update_from_dict({k: v for k, v in cli_other_spec_props.items() if v is not None})

    # Now compute the requirements list
    resolved_install_requires: Set[Requirement]
    implicitly_disabled: Set[Requirement]
    # Additional requirements that ComRAD imposes and which are mandatory.
    always_include_requires = {Requirement(COMRAD_PINNED_VERSION)}
    if cli_install_requires:
        # If you get a list of imports from outside, use that (e.g. coming from CLI args)
        resolved_install_requires = cli_install_requires
        _inject_mandatory_requirements(resolved_install_requires, always_include_requires)
        implicitly_disabled = set()
    else:
        # Otherwise do the import scanning procedure
        scanned_imports = scan_imports(entrypoint.parent)

        resolved_install_requires = {r for r in map(functools.partial(make_requirement_safe,
                                                                      error="The package won\'t be included in suggestions."),
                                                    scanned_imports)
                                     if r is not None}
        _specialize_requirements_to_currently_installed(resolved_install_requires)

        _inject_mandatory_requirements(resolved_install_requires, always_include_requires)
        implicitly_disabled = _disable_implicit_requirements(resolved_install_requires, always_include_requires)

    logger.debug(f'Found requirements: {resolved_install_requires}')
    if cached_spec_dict:
        cached_dep_names = set(cached_spec_dict.get('install_requires', []))
        resolved_dep_names = set(map(str, resolved_install_requires))
        if resolved_dep_names != cached_dep_names:
            logger.debug(f'Added packages: {resolved_dep_names - cached_dep_names}')
            logger.debug(f'Removed packages: {cached_dep_names - resolved_dep_names}')
    final_spec.install_requires = resolved_install_requires

    if interactive:
        # Finally confirm with the user that everything looks good
        confirm_spec_interactive(final_spec,
                                 force_phonebook=force_phonebook,
                                 implicitly_disabled_requirements=implicitly_disabled,
                                 mandatory=always_include_requires)

    try:
        final_spec.validate()
    except ValueError as e:
        raise AssertionError(f'Invalid package specification: {e!s}')
    written_file = dump_pyproject(spec=final_spec, project_root=entrypoint.parent)
    print(f'\nMetadata has been written into {written_file!s}!')


def _specialize_requirements_to_currently_installed(requirements: Set[Requirement]):
    python = Path(sys.executable)
    pip_freeze_output = subprocess.check_output([python, '-m', 'pip',
                                                 'list',
                                                 '--format', 'freeze']).decode()
    installed = set(map(Requirement, pip_freeze_output.splitlines()))
    for req in requirements.copy():
        for env_req in installed:
            if req.name == env_req.name:
                requirements.remove(req)
                requirements.add(env_req)


def _inject_mandatory_requirements(original: Set[Requirement], mandatory: Optional[Set[Requirement]]):
    if mandatory is None:
        return
    for mandatory_req in mandatory:
        # Remove any potential requirement that clashes (same name)
        for original_req in original.copy():
            if mandatory_req.name == original_req.name:
                original.remove(original_req)
        original.add(mandatory_req)


def _disable_implicit_requirements(input: Set[Requirement], mandatory: Optional[Set[Requirement]]) -> Set[Requirement]:
    # Returns implicitly disabled requirements. Original set stays with enabled requirements

    known_mandatory_names = set(map(operator.attrgetter('name'), mandatory)) if mandatory else set()
    given_reqs_map = {r.name: r for r in input}
    given_names = set(given_reqs_map.keys())
    optional_names = given_names - known_mandatory_names
    optional_map = {k: v for k, v in given_reqs_map.items() if k in optional_names}
    implicit_reqs: Set[Requirement] = set()

    comrad_reqs = _find_comrad_requirements()
    for comrad_req in comrad_reqs:
        try:
            original_req = optional_map[comrad_req.name]
            del optional_map[comrad_req.name]
        except KeyError:
            continue
        else:
            implicit_reqs.add(comrad_req)
            input.remove(original_req)

    return implicit_reqs


def _find_comrad_requirements() -> Set[Requirement]:
    comrad_pkg = importlib_metadata.distribution('comrad')  # type: ignore
    if comrad_pkg.requires is None:
        return set()
    return {Requirement(r) for r in comrad_pkg.requires if ' extra == ' not in r}
