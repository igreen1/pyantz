"""Test the abstract job module name."""

import importlib
import pathlib

import pyantz
from pyantz.infrastructure.config import abstract_job


def test_new_module_name_has_the_class() -> None:
    """The module with the correct spelling provides the base class."""
    assert abstract_job.AbstractJobConfig.__module__ == (
        "pyantz.infrastructure.config.abstract_job"
    )


def test_old_name_still_works_and_is_the_same_class() -> None:
    """Existing imports of the misspelled module give the very same class."""
    old = importlib.import_module("pyantz.infrastructure.config.abtrast_job")

    assert old.AbstractJobConfig is abstract_job.AbstractJobConfig
    assert old.str_uuid4 is abstract_job.str_uuid4


def test_nothing_imports_the_old_spelling() -> None:
    """No code in the package refers to the misspelled module (only its file exists)."""
    source = pathlib.Path(pyantz.__file__).parent
    offenders = [
        path.relative_to(source).as_posix()
        for path in source.rglob("*.py")
        if "abtrast" in path.read_text(encoding="utf-8")
    ]

    assert not offenders
