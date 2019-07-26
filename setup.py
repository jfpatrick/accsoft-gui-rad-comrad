#!/usr/bin/env python
import versioneer

from setuptools import setup, find_packages
from os import path

curr_dir = path.abspath(path.dirname(__file__))

with open(path.join(curr_dir, 'README.md'), 'r') as f:
    long_description = f.read()

with open(path.join(curr_dir, 'requirements.txt'), 'r') as f:
    requirements = f.read().split()

try:
    with open(path.join(curr_dir, 'test-requirements.txt'), 'r') as f:
        test_requirements = f.read().split()
except FileNotFoundError:
    # This is meant to be installed only from source, therefore pip installation is not supposed
    # to find this file
    test_requirements = []

try:
    with open(path.join(curr_dir, 'dev-requirements.txt'), 'r') as f:
        dev_requirements = f.read().split()
except FileNotFoundError:
    # This is meant to be installed only from source, therefore pip installation is not supposed
    # to find this file
    dev_requirements = []

setup(
    name='comrad',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='CO Multi-purpose Rapid Application Development framework',
    long_description=long_description,
    author='Ivan Sinkarenko',
    author_email='ivan.sinkarenko@cern.ch',
    url='https://wikis.cern.ch/display/ACCPY/Rapid+Application+Development',
    packages=find_packages(exclude='examples'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: Qt',
        'Operating System :: POSIX :: Linux',
    ],
    include_package_data=True,
    package_data={
        'comrad.qt': 'comrad/qt/*.ui',
        'comrad.tools': 'comrad/tools/*.ui',
        'comrad.designer.icons': 'comrad/designer/icons/*.ico',
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
        'dev': dev_requirements,
        'all': requirements + dev_requirements + test_requirements,
    },
    platforms=['centos7'],
    test_suite='tests',
)
