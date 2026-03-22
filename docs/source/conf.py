# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "PyAntz"
copyright = "2026, Ian Green"  # noqa: A001
author = "Ian Green"
release = "1.0.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx.ext.doctest",
]

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = "sphinx_book_theme"
html_static_path = ["_static"]


def skip_model_config(app, what, name, obj, skip, options):
    if name == "model_config":
        return True
    return skip

def setup(app):
    app.connect("autodoc-skip-member", skip_model_config)


autodoc_typehints = "description"
typehints_use_signature = True

autodoc_pydantic_model_show_json = True
autodoc_pydantic_settings_show_json = False
autodoc_pydantic_model_show_config_summary = False
add_module_names = False
