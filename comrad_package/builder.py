# Implementation of PEP-517 compatible backend
# https://www.python.org/dev/peps/pep-0517/
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Any, Optional
from jinja2 import FileSystemLoader, Environment
from _comrad.comrad_info import COMRAD_VERSION
from _comrad.package.spec import PackageSpec
from _comrad.package.pyproject import read_pyproject, InvalidProjectFileError, pyproject_dict_to_spec_dict


def build_wheel(wheel_directory: str,
                config_settings: Optional[Dict[str, Any]] = None,
                metadata_directory: Optional[str] = None) -> str:
    print('running build_wheel (ComRAD)')
    if config_settings:
        print(f'config settings: {config_settings}')
    # This import stays inside the method, to ensure that setuptools is installed, after inspection of
    # get_requires_for_build_wheel, and does not break module import of this file, if setuptools is missing.
    from setuptools import build_meta as setuptools_backend
    with _prepare_source_tree():
        print('calling build_wheel (setuptools)')
        wheel_filename = setuptools_backend.build_wheel(wheel_directory=wheel_directory,
                                                        config_settings=config_settings,
                                                        metadata_directory=metadata_directory)
        print(f'built wheel {(Path(wheel_directory) / wheel_filename)!s}')
        return wheel_filename


def build_sdist(sdist_directory: str, config_settings: Optional[Dict[str, Any]] = None) -> str:
    print('running build_sdist (ComRAD)')
    if config_settings:
        print(f'config settings: {config_settings}')
    # This import stays inside the method, to ensure that setuptools is installed, after inspection of
    # get_requires_for_build_sdist, and does not break module import of this file, if setuptools is missing.
    from setuptools import build_meta as setuptools_backend
    with _prepare_source_tree():
        print('calling build_sdist (setuptools)')
        sdist_filename = setuptools_backend.build_sdist(sdist_directory=sdist_directory,
                                                        config_settings=config_settings)
        print(f'built sdist {(Path(sdist_directory) / sdist_filename)!s}')
        return sdist_filename


def get_requires_for_build_wheel(config_settings: Optional[Dict[str, Any]] = None):
    return [*_get_common_requires(config_settings), 'wheel']


def get_requires_for_build_sdist(config_settings: Optional[Dict[str, Any]] = None):
    return _get_common_requires(config_settings)


def _get_common_requires(config_settings: Optional[Dict[str, Any]]):
    # All direct libraries (e.g. imported at the top of this file) are expected to be installed with comrad.
    # Here we add an additional constraint of "setuptools", which is relevant only for the isolated build environments.
    # Setuptools was chosen as a proxied build backend instead of higher-level pip, because pip does not provide
    # means to build sdist. setuptools is chosen to build both sdist and wheel instead of delegating wheel to pip
    # for the sake of consistency.
    _ = config_settings
    return ['setuptools>=50.0']


@contextmanager
def _prepare_source_tree():
    print(f'packaging ComRAD app source tree')
    cwd = Path.cwd()
    try:
        pyproject_dict = read_pyproject(project_root=cwd)
    except InvalidProjectFileError as e:
        print(f'failed to parse specification: {e!s}')
        exit(1)
    try:
        spec_dict = pyproject_dict_to_spec_dict(pyproject_dict)
        spec = PackageSpec.from_dict(spec_dict)
    except KeyError as e:
        print(f'failed to parse specification: Key not found - {e!s}')
        exit(1)
    try:
        spec.validate()
    except ValueError as e:
        print(f'failed to parse specification: {e!s}')
        exit(1)
    print(f'parsed specification for {spec.name}-{spec.version}')
    with TemporaryDirectory(prefix='comrad_package_') as tmp_dir:
        _generate_sources(source_path=cwd,
                          spec=spec,
                          output_path=Path(tmp_dir))
        os.chdir(tmp_dir)
        try:
            yield
        finally:
            os.chdir(cwd)


def _generate_sources(source_path: Path, spec: PackageSpec, output_path: Path):
    print(f'generating source tree in {output_path!s}')

    _render_file_template(tmpl_name='setup.py.j2',
                          dest=output_path / 'setup.py',
                          replacements={
                              'package': spec.to_dict(),
                          })

    qualified_name = spec.qualified_name
    pkg_subdir = output_path / qualified_name
    print(f'creating package source directory -> {pkg_subdir!s}')
    pkg_subdir.mkdir()

    _render_file_template(tmpl_name='__init__.py.j2',
                          dest=pkg_subdir / '__init__.py',
                          replacements={
                              'version': spec.version,
                          })

    src_dir = f'_payload_comrad_{qualified_name}'
    source_files_dir = pkg_subdir / src_dir
    print(f'copying user files {source_path!s} -> {source_files_dir!s}')
    shutil.copytree(source_path, source_files_dir)

    src_subdir_init = source_files_dir / '__init__.py'
    try:
        src_subdir_init.touch(exist_ok=False)
    except FileExistsError:
        pass
    else:
        print(f'generating __init__.py -> {src_subdir_init!s}')

    pyproject_file = source_files_dir / 'pyproject.toml'
    try:
        pyproject_file.unlink(missing_ok=True)  # type: ignore  # python 3.8 API
    except TypeError:
        try:
            pyproject_file.unlink()
        except FileNotFoundError:
            pass
        else:
            print(f'removing pyproject.toml -> {pyproject_file!s}')
    else:
        print(f'removing pyproject.toml -> {pyproject_file!s}')

    _render_file_template(tmpl_name='__main__.py.j2',
                          dest=pkg_subdir / '__main__.py',
                          replacements={
                              'entrypoint': spec.entrypoint,
                              'src_dir': src_dir,
                          })

    print(f'{spec.name}-{spec.version} source tree preparation finished!')


def _render_file_template(tmpl_name: str, replacements: Dict[str, Any], dest: Path):
    print(f'generating {dest.name} -> {dest!s}')
    loader = FileSystemLoader(searchpath=str(Path(__file__).parent / 'templates'))
    env = Environment(loader=loader, autoescape=True)
    tmpl = env.get_template(tmpl_name)
    contents = tmpl.render(tool_version=COMRAD_VERSION, **replacements)
    dest.write_text(contents)
