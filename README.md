# ComRAD

CO Multi-purpose Rapid Application Development

This framework integrates several tools to be used for developing applications in Python.
It allows for easy integration between CO control system and Qt GUI framework to produce
Operational GUI applications without much hassle.

>
> **[Read user documentation](https://acc-py.web.cern.ch/gitlab/acc-co/accsoft/gui/rad/accsoft-gui-rad-comrad/docs/stable)**
>

From here on, the information is related to the development of the framework...

# Contents
- [Description](#description)
- [Test](#test)
- [Development](#development)
  - [Linting](#linting)
  - [Building documentation](#building-documentation)
  - [Uploading package to CO package index](#uploading-package-to-co-package-index)

# Description

ComRAD is based on [PyDM](https://github.com/slaclab/pydm) environment developed in SLAC and
relies on custom [PyQt distribution](https://wikis.cern.ch/display/ACCPY/PyQt+distribution)
offered as a part of "Accelerating Python" initiative.

Currently, it integrates PyJAPC as an interface to the control system, but might support more
protocols in the future.

# Test

Considering that you have installed the package from source, navigate to the root directory,
and prepare test dependencies
```bash
pip install -e .[test]
```

Next, run tests:

```bash
python -m pytest
```

>
**Note!** Testing can be done in the randomized order to make sure that mocking does not
affect adjacent tests. To run in random order,
```bash
python -m pytest --random-order
```
>


# Development

For development, the easiest is to install all possible packages (to skip `pip install` in the
subsections):
```bash
pip install -e .[all]
```

## Linting

ComRAD is integrated with several linting utilities:

- [flake8](https://pypi.org/project/flake8/)
- [mypy](https://pypi.org/project/mypy/)
- [qsslint](https://github.com/KDAB/qsslint)

(we intentionally do not use [pylint](https://pypi.org/project/pylint/) because it creates too
much overhead)

Install required packages first:
```bash
pip install -e .[lint]
```

You would run each of them separately (from repository root).

For flake8:
```bash
flake8
```

For mypy (it does not handle PEP420 packages, so you'd need to specify them as arguments):
```bash
mypy . tests docs comrad/app comrad/app/plugins/toolbar comrad/data _comrad
```

For qsslint:
```bash
find . -name "*.qss" | xargs qsslint 
```

>
**Note!** qsslint needs to have access to the graphics stack, therefore running in Docker needs
more attention. Also, it's a custom tool, and we rely on it being the part of the PyQt
distribution.
>

## Building documentation

Install required packages first:
```bash
pip install -e .[doc]
```

Use [Sphinx](http://www.sphinx-doc.org/en/master/) to build the docs:
```bash
sphinx-build docs/ path/to/docs/output/dir
```

To browse it, just locate the `index.html`:
```bash
xdg-open path/to/docs/output/dir/index.html
```

Cross-referencing "Intersphinx" plugin takes heavy advantage of custom inventories
to create links for third-party libraries, such as Qt, PyQt and others. Not all of them
are available in the friendly way, that's why we have few custom inventories (located in
`docs/*.inv` files). These files are packaged using [sphobjinv](https://pypi.org/project/sphobjinv/)
tool from corresponding `docs/*.txt` files. If you want to add a missing symbol, modify
the `*.txt` file, re-create the inventory:
```bash
sphobjinv convert zlib --overwrite docs/<lib>.txt docs/<lib>.inv
```

Follow [this page](https://sphobjinv.readthedocs.io/en/v2.0/syntax.html) to understand the inventory
format.

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