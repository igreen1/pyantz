"""Test ``make_job`` error messages and import behavior."""

from __future__ import annotations

from typing import Any

import pytest

from pyantz.infrastructure.config import JobConfig, VirtualJobConfig, job
from pyantz.infrastructure.config.job import make_job

NOP = "pyantz.jobs.testing.nop.do_nothing"


def test_non_mapping_error_message() -> None:
    """A non-mapping config explains what was received."""
    with pytest.raises(TypeError, match="must be a mapping, got list"):
        make_job([1, 2, 3])


def test_missing_function_error_message() -> None:
    """A config without a function names the missing key."""
    with pytest.raises(ValueError, match="missing required key 'function'"):
        make_job({"parameters": {}})


def test_explicit_virtual_false_skips_import_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With `virtual` given, the function isn't imported to decide the type."""
    calls: list[Any] = []

    def _spy(key: Any) -> Any:  # noqa: ANN401
        calls.append(key)
        raise AssertionError

    monkeypatch.setattr(job, "import_module_item_by_name", _spy)

    result = make_job({"function": NOP, "parameters": {}, "virtual": False})

    assert isinstance(result, JobConfig)
    assert not calls


def test_virtual_detected_from_function() -> None:
    """Without `virtual`, it is looked up from the function."""
    virtual = make_job(
        {
            "function": "pyantz.virtual.add_variables.AddVariables",
            "parameters": {"variables": {}},
        },
    )
    assert isinstance(virtual, VirtualJobConfig)
    assert isinstance(make_job({"function": NOP, "parameters": {}}), JobConfig)
