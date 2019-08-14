from comrad import __version__, __author__
from datetime import datetime
import os

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

author_name = __author__.split(' <')[0]

project = 'ComRAD'
copyright = f'{datetime.now().year}, {author_name}'
author = author_name

# The full version, including alpha/beta/rc tags
release = __version__
version = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'recommonmark', # Enable Markdown source files along with reStructuredText
    'sphinx_rtd_theme', # Read-the-docs theme
    'sphinxcontrib.confluencebuilder',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_short_title = f'{project} v{__version__}'
html_title = f'{html_short_title} docs'

#html_logo # TODO: Put comrad logo here
#html_favicon # TODO: Put comrad logo here

# Enable Markdown source files along with reStructuredText
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Configure building docs for Confluence
confluence_publish = True
confluence_space_name = 'DEV' # TODO: Change space to Accpy
confluence_parent_page = 'BE-CO PyDM evaluation' # TODO: Change the parent page
confluence_server_url = 'https://wikis.cern.ch/'
confluence_server_user = 'isinkare'
confluence_ask_password = True
confluence_disable_ssl_validation = True  # Because CERN uses its own CA. Providing them both does not really help