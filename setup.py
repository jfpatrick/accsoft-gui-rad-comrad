#!/usr/bin/env python
import versioneer
import re
from setuptools import setup, find_packages
from os import path
from typing import List

curr_dir = path.abspath(path.dirname(__file__))

def read_req(f: str) -> List[str]:
    res = []
    for line in f.read().split('\n'):
        if not line.startswith('-e'):
            res.append(line)
            continue

        # Rearrange dev packages into the format understandable by setup()
        m = re.match('-e\ +((git\+(https?|ssh|git|krb5).*\.git([^#]*)?)(#egg=(.+)))', line)
        if m:
            addr = m.group(1)
            egg = m.group(6)
            res.append(f'{egg} @ {addr}')
    return res


with open(path.join(curr_dir, 'README.md'), 'r') as f:
    long_description = f.read()

with open(path.join(curr_dir, 'requirements.txt'), 'r') as f:
    requirements = read_req(f)

try:
    with open(path.join(curr_dir, 'test-requirements.txt'), 'r') as f:
        test_requirements = read_req(f)
except FileNotFoundError:
    # This is meant to be installed only from source, therefore pip installation is not supposed
    # to find this file
    test_requirements = []

try:
    with open(path.join(curr_dir, 'dev-requirements.txt'), 'r') as f:
        dev_requirements = read_req(f)
except FileNotFoundError:
    # This is meant to be installed only from source, therefore pip installation is not supposed
    # to find this file
    dev_requirements = []

print(test_requirements)
print(dev_requirements)
print(requirements)

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
        'comrad': 'comrad/*.qss',
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
