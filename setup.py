#!/usr/bin/env python
import versioneer
from setuptools import setup, PEP420PackageFinder
from pathlib import Path


# We use implicit packages (PEP420) that are not obliged
# to have __main__.py. Default implementation of setuptools.find_packages will
# expect that file to exist and thus skip everything else. We need a tailored
# version.
find_packages = PEP420PackageFinder.find


curr_dir: Path = Path(__file__).parent.absolute()


requirements = {
    'prod': [
        'numpy>=1.16.4,<2',
        'argcomplete>=1.10.0,<2',
        'colorlog>=4.0.2,<5',
        'QtPy>=1.7,<2',
        'pyjapc==2.2.0',  # We must keep it pinned to this version, because comrad is obliged to override getParam, which makes it very fragile to changes
        'accwidgets[graph,led,property_edit,timing_bar,log_console]>=1.0,<2a0',
        'papc>=0.5.1,<0.6',
        'pydm==1.10.7.post0',
        'JPype1>=0.7,<0.7.2',  # 0.7.2 seems incompatible with pyjapc as of now
        'dataclasses~=0.7;python_version<"3.7"',
        'pyccda~=0.10.1',
        'pyrbac==0.0.4',
    ],
    'test': [
        'pytest>=5.0.1,<5.1',
        'pytest-cov>=2.5.1,<2.6',
        'pytest-mock>=2.0,<2.1',
        'pytest-random-order>=1.0.4,<1.1',
        'pytest-qt>=3.2.2,<4',
        'freezegun>=0.3.15,<0.4',
    ],
    'lint': [
        'mypy==0.761',
        'flake8>=3.7.8,<3.8',
        'flake8-quotes>=2.1.0,<3',
        'flake8-commas>=2,<3',
        'flake8-colors>=0.1.6,<0.1.9a0',
        'flake8-rst>=0.7.1,<2',
        'flake8-breakpoint>=1.1.0,<2',
        'flake8-pyi>=19.3.0,<20',
        'flake8-comprehensions>=2.2.0,<3',
        'flake8-builtins-unleashed>=1.3.1,<2',
        'flake8-blind-except>=0.1.1,<2',
        'flake8-bugbear==20.1',
    ],
    'doc': [
        'Sphinx>=2.3.1,<3',
        'sphinx-rtd-theme>=0.4.3,<0.5',
        'sphinx-autodoc-typehints>=1.10.3,<1.11a0',
        'sphinxcontrib-napoleon2>=1.0,<2',
        'sphobjinv>=2.0,<2.1',
    ],
    'release': [
        'versioneer>=0.15',
        'setuptools>=40.8.0',
        'twine>=1.13.0,<1.14',
        'wheel',
    ],
}
requirements['dev'] = [*requirements['test'], *requirements['lint'], *requirements['doc'], *requirements['release']]
requirements['all'] = [*requirements['prod'], *requirements['dev']]

requires = requirements['prod']
del requirements['prod']
extra_requires = requirements


# Extracting author information, based on the approach of versioneer, similar how it shares version between runtime and
# packaging time.
def get_comrad_info(arg_name: str):
    import sys
    import re
    if 'versioneer' in sys.modules:
        # see the discussion in versioneer.py:get_cmdclass()
        del sys.modules['versioneer']
    root = versioneer.get_root()
    src_file = Path(root) / '_comrad/comrad_info.py'
    try:
        with src_file.open() as f:
            contents = f.read()
    except EnvironmentError:
        raise versioneer.NotThisMethod('unable to read comrad_info.py')
    mo = re.search(rf"{arg_name} = f?'([^']+)'", contents)
    if mo is None or mo.lastindex is None:
        mo = re.search(rf'{arg_name} = f?"""([^(""")]+)"""', contents)
    if mo is None:
        raise ValueError(f'unable to locate {arg_name} in comrad_info.py')
    return mo.group(1)


# Note include_package_data must be set to False, otherwise setuptools
# will consider only CVS/Svn tracked non-code files
# More info: https://stackoverflow.com/a/23936405
setup(
    name='comrad',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description=get_comrad_info('COMRAD_DESCRIPTION_SHORT'),
    long_description=get_comrad_info('COMRAD_DESCRIPTION_LONG'),
    author=get_comrad_info('COMRAD_AUTHOR_NAME'),
    author_email=get_comrad_info('COMRAD_AUTHOR_EMAIL'),
    url=get_comrad_info('COMRAD_WIKI'),
    license='None (internal package)',
    packages=find_packages(exclude=('build*', 'dist*', 'docs*', 'tests*', '*.egg-info')),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Typing :: Typed',
    ],
    package_data={
        '': ['*.ui', '*.ico', '*.png', '*.qss', '*.json', '*.txt'],
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
