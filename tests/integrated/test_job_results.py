"""Test how the value returned by a job function is interpreted."""

import logging
from typing import TYPE_CHECKING, Any

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.runner.job_manager import run_job

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    import pytest


def _job(function: Callable[..., Any], job_id: str = "my_job") -> JobWithContext:
    return JobWithContext.model_validate(
        {"job_id": job_id, "function": function, "parameters": {}},
    )


def _return(value: object) -> Callable[..., Any]:
    def _fn(_params: Mapping[str, Any], _submit: Any) -> Any:  # noqa: ANN401
        return value

    return _fn


def test_none_result_warns_and_succeeds(caplog: pytest.LogCaptureFixture) -> None:
    """A function returning None is a success, with a warning."""
    with caplog.at_level(logging.WARNING):
        assert run_job(_job(_return(None)), lambda *_: None) is True

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "my_job" in warnings[0].getMessage()
    assert "None" in warnings[0].getMessage()


def test_other_non_bool_results_use_truthiness(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Other non-bool results warn and are judged by truthiness."""
    with caplog.at_level(logging.WARNING):
        assert run_job(_job(_return("done")), lambda *_: None) is True
        assert run_job(_job(_return(0)), lambda *_: None) is False

    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 2  # noqa: PLR2004


def test_bool_results_do_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    """True and False are the documented results and are silent."""
    with caplog.at_level(logging.WARNING):
        assert run_job(_job(_return(value=True)), lambda *_: None) is True
        assert run_job(_job(_return(value=False)), lambda *_: None) is False

    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


def test_result_log_line_order(caplog: pytest.LogCaptureFixture) -> None:
    """The debug line reads `Job (<id>) returned result <result>`."""
    with caplog.at_level(logging.DEBUG):
        run_job(_job(_return(value=True), job_id="abc"), lambda *_: None)

    assert "Job (abc) returned result True" in caplog.text


def test_start_is_logged_once(caplog: pytest.LogCaptureFixture) -> None:
    """The 'Starting running' line isn't duplicated."""
    with caplog.at_level(logging.DEBUG):
        run_job(_job(_return(value=True)), lambda *_: None)

    assert caplog.text.count("Starting running") == 1
