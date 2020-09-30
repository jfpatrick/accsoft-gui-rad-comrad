import logging
import sys
import functools
import subprocess
import operator
from pathlib import Path
from typing import Dict, Optional, Set, Any
from packaging.requirements import Requirement, InvalidRequirement
from _comrad.comrad_info import COMRAD_VERSION
from .importlib_shim import find_distribution_name, importlib_metadata
from .spec import PackageSpec
from .spec_cache import read_spec_cache, dump_spec_cache
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


def build_spec(entrypoint: Path,
               interactive: bool,
               pkg_spec_overloads: Optional[Dict[str, Any]] = None,
               install_requires: Optional[Set[Requirement]] = None) -> PackageSpec:
    """
    Creates a proposed specification of the package to build.

    Args:
        entrypoint: Path to the entrypoint file of the ComRAD application. This has to be either *.py or *.ui file.
        interactive: Whether create a spec in interactive mode. When :obj:`True`, the user will be asked questions and
                     given choices.
        pkg_spec_overloads: High-priority overloads that can override any properties of the default spec. This is
                            expected to come from the CLI arguments.
        install_requires: Initial set of requirements that can be supplied via CLI arguments.

    Returns:
        Created specification.
    """
    _assert_condition(entrypoint.exists() and entrypoint.is_file(), f'Specified file "{entrypoint!s}" is not found')
    _assert_condition(entrypoint.suffix in ['.ui', '.py'], 'Only Python files (*.py) or Designer files (*.ui) are supported')
    default_spec = PackageSpec(name=entrypoint.stem,
                               version='0.0.1',
                               install_requires=set())
    final_spec = default_spec

    cached_spec: Optional[PackageSpec]
    try:
        cached_spec = read_spec_cache(entrypoint)
    except FileNotFoundError:
        cached_spec = None
    else:
        final_spec.update(cached_spec)

    if pkg_spec_overloads:
        # Update with "higher-priority" settings (e.g. coming from CLI args)
        final_spec.update_from_dict({k: v for k, v in pkg_spec_overloads.items() if v})

    # Now compute the requirements list
    resolved_install_requires: Set[Requirement]
    implicitly_disabled: Set[Requirement]
    # Additional requirements that ComRAD imposes and which are mandatory.
    always_include_requires = {Requirement(f'comrad=={COMRAD_VERSION}')}
    if install_requires:
        # If you get a list of imports from outside, use that (e.g. coming from CLI args)
        resolved_install_requires = install_requires
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
    if cached_spec and resolved_install_requires != cached_spec.install_requires:
        logger.debug(f'Added packages: {resolved_install_requires - cached_spec.install_requires}')
        logger.debug(f'Removed packages: {cached_spec.install_requires - resolved_install_requires}')
    final_spec.install_requires = resolved_install_requires

    if interactive:
        # Finally confirm with the user that everything looks good
        confirm_spec_interactive(final_spec,
                                 implicitly_disabled_requirements=implicitly_disabled,
                                 mandatory=always_include_requires)

    try:
        final_spec.validate()
    except ValueError as e:
        logger.error(f'Invalid package specification: {e!s}')
        exit(1)
    dump_spec_cache(spec=final_spec, entrypoint=entrypoint)
    return final_spec


def _assert_condition(condition: bool, message: str):
    if not condition:
        logger.error(message)
        exit(1)


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
