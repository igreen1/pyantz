# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from __future__ import annotations

import inspect
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


def skip_member(app, what, name, obj, skip, options):
    if name == "model_config":
        return True
    # sqlalchemy adds these to the orm base class, with sqlalchemy's docs
    if what == "class" and name in {"metadata", "registry"}:
        return True
    # autodoc drops imported classes and functions only after processing their
    # docstrings, which fails or warns for some of other packages' docstrings
    if (
        what == "module"
        and (inspect.isclass(obj) or inspect.isroutine(obj))
        and not (getattr(obj, "__module__", None) or "").startswith("pyantz")
    ):
        return True
    return skip


def setup(app):
    app.connect("autodoc-skip-member", skip_member)


# document each object in its own module only, not again where it is re-exported
autodoc_default_options = {"ignore-module-all": True}
autodoc_typehints = "description"
typehints_use_signature = True

autodoc_pydantic_model_show_json = True
autodoc_pydantic_settings_show_json = False
autodoc_pydantic_model_show_config_summary = False
add_module_names = False
