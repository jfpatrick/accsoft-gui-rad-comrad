#!/usr/bin/env python
import versioneer
from setuptools import setup, PEP420PackageFinder
from pathlib import Path


# We use implicit packages (PEP420) that are not obliged
# to have __init__.py. Default implementation of setuptools.find_packages will
# expect that file to exist and thus skip everything else. We need a tailored
# version.
find_packages = PEP420PackageFinder.find


curr_dir: Path = Path(__file__).parent.absolute()


with curr_dir.joinpath('README.md').open() as f:
    long_description = f.read()


requirements = {
    'prod': [
        'numpy>=1.16.4&&<2',
        'argcomplete>=1.10.0&&<2',
        'colorlog>=4.0.2&&<5',
        'QtPy>=1.7&&<2',
        'pyjapc @ git+ssh://git@gitlab.cern.ch:7999/pelson/pyjapc.git@jvm_startup_hook#egg=pyjapc',
        'accwidgets>=0.1.1&&accwidgets<1',
        'papc @ git+ssh://git@gitlab.cern.ch:7999/pelson/papc.git#egg=papc',
        'pydm @ git+ssh://git@gitlab.cern.ch:7999/acc-co/accsoft/gui/rad/accsoft-gui-rad-pydm.git@multi-fix#egg=pydm',
    ],
    'test': [
        'pytest>=5.0.1&&<5.1',
        'pytest-cov>=2.5.1&&<2.6',
        'pytest-mock>=2.0&&<2.1',
        'pytest-random-order>=1.0.4&&<1.1',
    ],
    'lint': [
        'mypy==0.761',
        'flake8>=3.7.8&&<4',
        'flake8-quotes>=2.1.0&&<3',
        'flake8-commas>=2&&<3',
        'flake8-colors>=0.1.6&&<2',
        'flake8-rst>=0.7.1&&<2',
        'flake8-breakpoint>=1.1.0&&<2',
        'flake8-pyi>=19.3.0&&<20',
        'flake8-comprehensions>=2.2.0&&<3',
        'flake8-builtins-unleashed>=1.3.1&&<2',
        'flake8-blind-except>=0.1.1&&<2',
        'flake8-bugbear==20.1',
    ],
    'docs': [
        'Sphinx>=2.1.2&&<2.2',
        'recommonmark>=0.6.0&&<0.7',
        'sphinx-rtd-theme>=0.4.3&&<0.5',
    ],
    'release': [
        'versioneer>=0.15',
        'setuptools>=40.8.0',
        'twine>=1.13.0&&<1.14',
        'wheel',
    ],
}
requirements['dev'] = [*requirements['test'], *requirements['lint'], *requirements['docs'], *requirements['release']]
requirements['all'] = [*requirements['prod'], *requirements['dev']]

requires = requirements['prod']
del requirements['prod']
extra_requires = requirements

# Note include_package_data must be set to False, otherwise setuptools
# will consider only CVS/Svn tracked non-code files
# More info: https://stackoverflow.com/a/23936405
setup(
    name='comrad',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='CO Multi-purpose Rapid Application Development framework',
    long_description=long_description,
    author='Ivan Sinkarenko',
    author_email='ivan.sinkarenko@cern.ch',
    url='https://wikis.cern.ch/display/ACCPY/Rapid+Application+Development',
    packages=find_packages(exclude=('build*', 'dist*', 'docs*', 'tests', '*.egg-info')),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Typing :: Typed',
    ],
    package_data={
        '': ['*.ui', '*.ico', '*.png', '*.qss', '*.json'],
    },
    install_requires=requires,
    entry_points={
        'gui_scripts': [
            'comrad=_comrad.launcher:run',
        ],
    },
    extras_require=extra_requires,
    platforms=['centos7'],
    test_suite='tests',
)
