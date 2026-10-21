"""Test the variables of the running job are restored after it finishes."""

from __future__ import annotations

from typing import Any

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.runner.job_manager import JobVariables, run_job

seen: list[Any] = []


def record(_params: Any, _submit: Any) -> bool:  # noqa: ANN401
    """Remember which variables the job sees."""
    seen.append(JobVariables.get())
    return True


def record_then_raise(_params: Any, _submit: Any) -> bool:  # noqa: ANN401
    """Remember the variables, then fail."""
    seen.append(JobVariables.get())
    msg = "boom"
    raise RuntimeError(msg)


def _job(function: Any, variables: dict[str, Any]) -> JobWithContext:  # noqa: ANN401
    return JobWithContext.model_validate(
        {"function": function, "parameters": {}, "variables": variables},
    )


def setup_function() -> None:
    """Start each test with nothing recorded."""
    seen.clear()


def test_job_sees_its_variables_and_they_are_reset() -> None:
    """Inside the job the variables are set; afterwards they are gone."""
    assert JobVariables.get() is None

    assert run_job(_job(record, {"a": 1}), lambda *_: None) is True

    assert seen == [{"a": 1}]
    assert JobVariables.get() is None


def test_variables_are_reset_when_the_job_raises() -> None:
    """A failing job doesn't leave its variables behind."""
    assert run_job(_job(record_then_raise, {"a": 1}), lambda *_: None) is False

    assert seen == [{"a": 1}]
    assert JobVariables.get() is None


def test_nested_run_restores_the_parents_variables() -> None:
    """A job run from within another job puts the outer variables back."""
    after_inner: list[Any] = []

    def outer(_params: Any, _submit: Any) -> bool:  # noqa: ANN401
        run_job(_job(record, {"inner": True}), lambda *_: None)
        after_inner.append(JobVariables.get())
        return True

    assert run_job(_job(outer, {"outer": True}), lambda *_: None) is True

    assert seen == [{"inner": True}]
    assert after_inner == [{"outer": True}]
