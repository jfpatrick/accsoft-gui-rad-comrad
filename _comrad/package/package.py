import logging
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional, Set
from jinja2 import FileSystemLoader, Environment
from packaging.requirements import Requirement
from _comrad.comrad_info import COMRAD_VERSION
from .spec import PackageSpec
from .spec_builder import build_spec


logger = logging.getLogger('comrad.package')


def package_wheel(entrypoint: Path,
                  output_path: Path,
                  pkg_spec_overloads: Optional[Dict[str, Any]] = None,
                  install_requires: Optional[Set[Requirement]] = None,
                  interactive: bool = False):
    """
    Package ComRAD application into a binary wheel.

    Args:
        entrypoint: Path to the entrypoint file of the ComRAD application. This has to be either *.py or *.ui file.
        output_path: Directory to create the wheel in.
        pkg_spec_overloads: High-priority overloads that can override any properties of the default spec. This is
                            expected to come from the CLI arguments.
        install_requires: Initial set of requirements that can be supplied via CLI arguments.
        interactive: Whether create a spec in interactive mode. When :obj:`True`, the user will be asked questions and
                     given choices.
    """
    spec = build_spec(entrypoint=entrypoint,
                      interactive=interactive,
                      pkg_spec_overloads=pkg_spec_overloads,
                      install_requires=install_requires)

    with TemporaryDirectory(prefix='comrad_package_') as tmp_dir:
        dest = Path(tmp_dir)
        logger.info(f'Packaging {spec.name} {spec.version}')
        package_dir = dest / 'build'
        generate_sources(entrypoint=entrypoint,
                         spec=spec,
                         output_path=package_dir)

        wheel_dir = dest / 'wheelhouse'
        build_wheel(src=package_dir, dest=wheel_dir)
        for whl in wheel_dir.glob('*.whl'):
            shutil.copy(whl, output_path)
            logger.info(f'Built wheel {(output_path / whl.name)!s}')


def generate_sources(entrypoint: Path, spec: PackageSpec, output_path: Path):
    """
    Create a complete Python package.

    Args:
        entrypoint: Entrypoint file of the ComRAD application. This must be either ``*.py`` or ``*.ui`` file.
        spec: Complete specification of the package, which will influence contents of ``setup.py``.
        output_path: Location to store the sources in.
    """
    logger.debug(f'Making a package inside {output_path!s}')
    output_path.mkdir(parents=True)

    logger.debug(f'Generating setup.py')
    render_file_template(tmpl_name='setup.py.j2',
                         dest=output_path / 'setup.py',
                         replacements={
                             'package': spec.to_dict(),
                         })

    logger.debug(f'Creating package source directory')
    pkg_subdir = output_path / spec.name.replace('-', '_')
    pkg_subdir.mkdir()

    logger.debug(f'Generating __init__.py')
    render_file_template(tmpl_name='__init__.py.j2',
                         dest=pkg_subdir / '__init__.py',
                         replacements={
                             'version': spec.version,
                         })

    logger.debug(f'Copying user files')
    source_files_dir = pkg_subdir / SRC_DIR
    shutil.copytree(entrypoint.parent, source_files_dir)

    logger.debug(f'Generating __main__.py')
    render_file_template(tmpl_name='__main__.py.j2',
                         dest=pkg_subdir / '__main__.py',
                         replacements={
                             'entrypoint': entrypoint.name,
                             'src_dir': SRC_DIR,
                         })

    logger.debug(f'{entrypoint} packaging finished!')


def build_wheel(src: Path, dest: Path):
    """
    Build a wheel out of pre-generated package sources.

    Args:
        src: Path to the package sources.
        dest: Output directory to place the wheel.
    """
    python = Path(sys.executable)
    subprocess.check_output([python, '-m', 'pip',
                             'wheel',
                             '--no-deps',
                             '--no-index',
                             '--wheel-dir', dest,
                             src])


def render_file_template(tmpl_name: str, replacements: Dict[str, Any], dest: Path):
    """
    Renders a template with given replacements.

    Args:
        tmpl_name: Name of the template file, located inside "templates" subdirectory.
        replacements: Key-value pairs to be replaced inside the template.
        dest: Resulting output file.
    """
    loader = FileSystemLoader(searchpath=str(Path(__file__).parent / 'templates'))
    env = Environment(loader=loader, autoescape=True)
    tmpl = env.get_template(tmpl_name)
    contents = tmpl.render(tool_version=COMRAD_VERSION, **replacements)
    dest.write_text(contents)


SRC_DIR = 'src'
