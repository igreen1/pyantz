"""Test that ``strict`` rejects unresolved variables in typed parameters."""

from typing import Any

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config import JobWithContext

TOUCH = "pyantz.jobs.testing.touch_file.touch_file"


def _job(*, strict: bool, parameters: dict[str, Any]) -> JobWithContext:
    return JobWithContext.model_validate(
        {
            "function": TOUCH,
            "parameters": parameters,
            "variables": {"known": True},
            "strict": strict,
        },
    )


def test_strict_rejects_unresolved_variable() -> None:
    """`exist_ok` is a bool; an unset variable can't satisfy it in strict mode."""
    with pytest.raises(ValidationError):
        _job(strict=True, parameters={"path": "x", "exist_ok": "%{missing}"})


def test_non_strict_allows_unresolved_variable() -> None:
    """Without strict, the variable may still be set at runtime by another job."""
    job = _job(strict=False, parameters={"path": "x", "exist_ok": "%{missing}"})
    assert job.parameters["exist_ok"] == "%{missing}"


def test_strict_accepts_resolvable_variable() -> None:
    """Strict mode still allows variables which are set."""
    job = _job(strict=True, parameters={"path": "x", "exist_ok": "%{known}"})
    assert job.strict
