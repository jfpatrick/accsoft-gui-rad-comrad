#!/usr/bin/env python
import versioneer
import re
from setuptools import setup, PEP420PackageFinder
from os import path
from typing import List, TextIO


# We use implicit packages (PEP420) that are not obliged
# to have __init__.py. Default implementation of setuptools.find_packages will
# expect that file to exist and thus skip everything else. We need a tailored
# version.
find_packages = PEP420PackageFinder.find


curr_dir = path.abspath(path.dirname(__file__))


def read_req(f: TextIO) -> List[str]:
    res = []
    for line in f.read().split('\n'):
        if not line.startswith('-e'):
            res.append(line)
            continue

        # Rearrange dev packages into the format understandable by setup()
        m = re.match(r'-e\ +((git\+(https?|ssh|git|krb5).*\.git([^#]*)?)(#egg=(.+)))', line)
        if m:
            addr = m.group(1)
            egg = m.group(6)
            res.append(f'{egg} @ {addr}')
    return res


with open(path.join(curr_dir, 'README.md'), 'r') as f:
    long_description = f.read()

with open(path.join(curr_dir, 'requirements.txt'), 'r') as f:
    requirements = read_req(f)


def read_extras_req(filename: str):
    try:
        with open(path.join(curr_dir, filename), 'r') as f:
            return read_req(f)
    except FileNotFoundError:
        # This is meant to be installed only from source, therefore pip installation is not supposed
        # to find this file
        return []


test_requirements = read_extras_req('test-requirements.txt')
docs_requirements = read_extras_req('docs-requirements.txt')
dev_requirements = read_extras_req('dev-requirements.txt')

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
        'Operating System :: POSIX :: Linux',
    ],
    package_data={
        '': ['*.ui', '*.ico', '*.png', '*.qss', '*.json'],
    },
    install_requires=requirements,
    entry_points={
        'gui_scripts': [
            'comrad_designer=comrad.launcher.main:designer',
            'comrun=comrad.launcher.main:pydm',
        ],
    },
    extras_require={
        'test': test_requirements,
        'docs': docs_requirements,
        'dev': dev_requirements,
        'all': requirements + dev_requirements + test_requirements + docs_requirements,
    },
    platforms=['centos7'],
    test_suite='tests',
)
