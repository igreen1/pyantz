"""Test the registry of jobs."""

import importlib

import pyantz.jobs  # noqa: F401  (registers the jobs)
from pyantz.infrastructure.config.parameters.decorators import get_registered_functions


def _names() -> list[str]:
    return sorted(fn.PYANTZ_NAME for fn in get_registered_functions())  # ty: ignore[unresolved-attribute]


def test_changing_the_result_does_not_change_the_registry() -> None:
    """The returned list is a copy."""
    before = _names()

    returned = get_registered_functions()
    returned.clear()

    assert _names() == before
    assert get_registered_functions()


def test_each_call_returns_a_new_list() -> None:
    """Two calls don't share a list."""
    assert get_registered_functions() is not get_registered_functions()


def test_reloading_a_job_module_does_not_duplicate_it() -> None:
    """Registering the same job again replaces the entry."""
    before = _names()

    importlib.reload(importlib.import_module("pyantz.jobs.testing.touch_file"))

    after = _names()
    assert after == before
    assert after.count("pyantz.jobs.testing.touch_file.touch_file") == 1
