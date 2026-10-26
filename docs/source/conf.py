"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyantz

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Options

sys.path.insert(0, str(Path("..").resolve()))

project = "PyAntz"
copyright = "2026, Ian Green"  # noqa: A001
author = "Ian Green"
# the version bumpver keeps in src/pyantz/__init__.py, so the docs move with it
release = pyantz.__version__
version = ".".join(release.split(".")[:2])

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


def skip_member(  # noqa: PLR0913, PLR0917
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,  # noqa: ANN401
    skip: bool,  # noqa: FBT001
    options: Options,
) -> bool:
    """Leave out members which shouldn't be documented.

    Connected to autodoc's ``autodoc-skip-member`` event.

    Args:
        app: the sphinx application (unused).
        what: the type of the object the member belongs to, e.g., ``"module"``.
        name: the member's name.
        obj: the member.
        skip: whether autodoc would skip the member.
        options: the options of the autodoc directive (unused).

    Returns:
        bool: True to skip the member, otherwise autodoc's own decision.

    Raises:
        None.

    """
    del app, options
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


def label_job_parameters(  # noqa: PLR0913, PLR0917
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,  # noqa: ANN401
    options: Options,
    lines: list[str],
) -> None:
    """Relabel the "Parameters" section of job functions as "Job parameters".

    Napoleon renders a job's ``Parameters:`` section (the fields of its parameters
    model) as a ``:Parameters:`` field; sphinx labels the function's own arguments
    "Parameters" too, so give the job's fields a label of their own. Connected to
    autodoc's ``autodoc-process-docstring`` event.

    Args:
        app: the sphinx application (unused).
        what: the type of the object (unused).
        name: the object's full name (unused).
        obj: the object (unused).
        options: the options of the autodoc directive (unused).
        lines: the docstring's lines, after napoleon; edited in place.

    Returns:
        None.

    Raises:
        None.

    """
    del app, what, name, obj, options
    for i, line in enumerate(lines):
        if line.startswith(":Parameters:"):
            lines[i] = ":Job parameters:" + line.removeprefix(":Parameters:")


def setup(app: Sphinx) -> None:
    """Connect this configuration's event handlers.

    Args:
        app: the sphinx application.

    Returns:
        None.

    Raises:
        None.

    """
    app.connect("autodoc-skip-member", skip_member)
    # after napoleon (priority 500) has turned the docstring into rst
    app.connect("autodoc-process-docstring", label_job_parameters, priority=600)


# document each object in its own module only, not again where it is re-exported;
# private helpers are documented (and their examples tested) too
autodoc_default_options = {"ignore-module-all": True, "private-members": True}
autodoc_typehints = "description"
typehints_use_signature = True
# sphinx-autodoc-typehints can't import the `TYPE_CHECKING` imports of
# sqlalchemy.orm.instrumentation (relative imports), which isn't our code
suppress_warnings = ["sphinx_autodoc_typehints.guarded_import"]

# a job function's "Parameters:" section lists the fields of its parameters model;
# it is kept apart from "Args:" (the function's own arguments) instead of being
# napoleon's alias for it
napoleon_custom_sections = [("Parameters", "params_style")]

autodoc_pydantic_model_show_json = True
autodoc_pydantic_settings_show_json = False
autodoc_pydantic_model_show_config_summary = False
add_module_names = False
