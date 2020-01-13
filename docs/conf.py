from typing import List
from datetime import datetime
from comrad import __version__, __author__

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

author_name = __author__.split('<')[0].strip()

project = 'ComRAD'
copyright = f'{datetime.now().year}, CERN'
author = author_name

# The full version, including alpha/beta/rc tags
release = __version__
version = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'recommonmark',  # Enable Markdown source files along with reStructuredText
    'sphinx_rtd_theme',  # Read-the-docs theme
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinxcontrib.napoleon',
    'sphinx_autodoc_typehints',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: List[str] = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

html_short_title = f'{project} v{__version__}'
html_title = f'{html_short_title} docs'

html_logo = '../../comrad/icons/app.ico'
html_favicon = html_logo

# This value controls the docstrings inheritance. If set to True the docstring for classes or methods,
# if not explicitly set, is inherited form parents.
autodoc_inherit_docstrings = True
# Scan all found documents for autosummary directives, and generate stub pages for each.
autosummary_generate = True
# Document classes and functions imported in modules
autosummary_imported_members = True
# if True, set typing.TYPE_CHECKING to True to enable “expensive” typing imports
set_type_checking_flag = True


# Enable Markdown source files along with reStructuredText
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
