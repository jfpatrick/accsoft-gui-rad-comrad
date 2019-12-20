# ComRAD

CO Multi-purpose Rapid Application Development

This framework integrates several tools to be used for developing applications in Python.
It allows for easy integration between CO control system and Qt GUI framework to produce Operational GUI applications without much hassle.

# Contents
- [Description](#description)
- [Install](#install)
  - [pip from CO package index](#pip-from-co-package-index)
  - [pip from Gitlab](#pip-from-gitlab)
  - [From source](#from-source)
- [Usage](#usage)
  - [Edit UI in ComRAD Designer](#edit-ui-in-comrad-designer)
  - [Run the application](#run-the-application)
- [Test](#test)
  - [Code coverage](#code-coverage)
- [Development](#development)
  - [Linting](#linting)
  - [Package hierarchy](#package-hierarchy)
  - [Building documentation](#building-documentation)
    - [Confluence](#confluence)
    - [Self-hosted web](#self-hosted-web)
  - [Uploading package to CO package index](#uploading-package-to-co-package-index)

# Description

ComRAD is based on [PyDM](https://github.com/slaclab/pydm) environment developed in SLAC and relies on custom
[PyQt distribution](https://wikis.cern.ch/display/ACCPY/PyQt+distribution) offered as a part of "Accelerating Python" initiative.

Currently, it integrates PyJAPC as an interface to the control system, but might support more protocols in the future.

# Install

Before performing any operations or installation make sure that you have PyQt distribution active.

## pip from CO package index

```bash
pip install comrad
```

## pip from Gitlab

```bash
pip install git+https://gitlab.cern.ch/acc-co/accsoft/gui/rad/accsoft-gui-rad-comrad.git
```

## From source

```bash
git clone https://gitlab.cern.ch/acc-co/accsoft/gui/rad/accsoft-gui-rad-comrad.git
cd accsoft-gui-rad-comrad
pip install .
```

## Setup auto-completion

ComRAD takes advantage of `argcomplete` - an auto-completion assistant. To have auto-completion enabled for
`comrad` commands, you need to activate it.

1. If you are **not** using virtual environments and have installed comrad globally, you can use global
activation - in this case the auto-completion will be available in every terminal session
([More info](https://github.com/kislyuk/argcomplete#activating-global-completion)):
```bash
activate-global-python-argcomplete
```

2. If you are using virtual environments, `argcomplete` will likely be installed there. What's more important,
`comrad` will be installed inside virtual environment. Thus, even if you had global activation, it would not
find it. Hence, you need to activate auto-completion every time. Most conveniently it's done by augmenting
`activate` script:
```bash
echo 'eval "$(register-python-argcomplete comrad)"' >> venv/bin/activate
```

3. Regardless, you can modify your `~/.bashrc` script to run this activations for the new session, if you
desire so.

# Usage

To find out the usage of ComRAD, use the help commadn:
```bash
comrad -h
```
## Edit UI in ComRAD Designer

Run the command
```bash
comrad designer
```

or

```bash
comrad designer my_interface.ui
```

## Run the application

Run the command
```bash
comad run my_interface.ui
```
or
```bash
comad run my_app.py
```

# Test

Considering that you have installed the package from source, navigate to the root directory, and prepare test dependencies
```bash
pip install -e .[test]
```

Next, run tests:

```bash
python -m pytest
```

>
**Note!** Testing can be done in the randomized order to make sure that mocking does not affect adjacent tests. To run in random order,
```bash
python -m pytest --random-order
```
>

## Code coverage

You can also collect coverage information.
>
**Note!** Currently pytest-cov may report incorrect coverage.
It is suggested to use `coverage` command directly to produce accurate results:

```bash
coverage run --source rad -m py.test && coverage report -m
```

or for HTML version: 
```bash
coverage run --source rad -m py.test && coverage html
```
>

# Development

## Linting

ComRAD is integrated with several linting utilities:

- flake8
- mypy

(we intentionally do not use pylint because it creates too much overhead)

You would run each of them separately (from repository root).

For flake8:
```bash
flake8
```

For mypy:
```bash
mypy .
```

## Building documentation

Use sphinx to build the docs:
```bash
cd docs
```

### Confluence

Prefered way, would be to build the documentation for confluence. We want to keep all the documentation in the same place.
To build new version of docs for confluence, simply run

```bash
make confluence
```

and enter confluence password.

>
If you want to upload the docs with a different confluence user that default, locate variable `confluence_server_user` in
`docs/source/conf.py` and change it to your confluence user.
>

### Self-hosted web

To build a HTML documentation, run

```bash
make html
```

and locate the index page in `docs/build/index.html`.

## Uploading package to CO package index
Make sure that you have tools installed
```bash
pip install .[release]
```
Prepare the source distribution
```bash
python setup.py sdist bdist_wheel
```

Upload to the repository
```bash
python -m twine upload --repository-url http://acc-py-repo:8081/repository/py-release-local/ -u py-service-upload dist/*
```

And now you can clean up
```bash
rm -rf build dist *.egg-info
```