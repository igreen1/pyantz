"""Test jobs which run for too long are stopped."""

import os
import time
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from pyantz import start
from pyantz.infrastructure.config import JobConfig
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path

DISPATCH = "pyantz.jobs.subproc.dispatch.dispatch"
TOUCH = "pyantz.jobs.testing.touch_file.touch_file"
SLEEP_SECONDS = 20


def _run(tmp_path: Path, jobs: list[dict[str, Any]]) -> tuple[SqliteQueue, float]:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    started = time.monotonic()
    start(
        {
            "jobs": jobs,
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": True,
                "poll_timeout": 0.01,
                "working_directory": os.fspath(work),
            },
        },
    )
    return SqliteQueue(work / "queue.db"), time.monotonic() - started


def _sleeper(**extra: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "function": DISPATCH,
        "parameters": {"cmd": ["sleep", str(SLEEP_SECONDS)]},
        **extra,
    }


def test_slow_job_is_stopped_and_the_worker_goes_on(tmp_path: Path) -> None:
    """A job over its limit ends as an error and the next job still runs."""
    after = tmp_path / "after"
    jobs = [
        _sleeper(job_id="slow", timeout_seconds=1),
        {"function": TOUCH, "parameters": {"path": os.fspath(after)}},
    ]

    queue, elapsed = _run(tmp_path, jobs)

    report = queue.get_jobs_report()
    assert (report.error, report.success) == (1, 1)
    assert after.exists()
    assert elapsed < SLEEP_SECONDS / 2


def test_dependents_of_a_timed_out_job_fail(tmp_path: Path) -> None:
    """Timing out is a failure like any other."""
    after = tmp_path / "after"
    jobs = [
        _sleeper(job_id="slow", timeout_seconds=1),
        {
            "depends_on": ["slow"],
            "function": TOUCH,
            "parameters": {"path": os.fspath(after)},
        },
    ]

    queue, _ = _run(tmp_path, jobs)

    assert queue.get_jobs_report().error == 2  # noqa: PLR2004
    assert not after.exists()


def test_job_within_its_limit_succeeds_and_can_submit_jobs(tmp_path: Path) -> None:
    """Jobs with a limit run in their own process but behave the same."""
    child = tmp_path / "child"
    jobs = [
        {
            "timeout_seconds": 30,
            "function": "pyantz.jobs.branching.if_else.conditionally_execute",
            "parameters": {
                "left_side": 1,
                "right_side": 1,
                "comparator": "==",
                "if_true": {
                    "function": TOUCH,
                    "parameters": {"path": os.fspath(child)},
                },
            },
        },
    ]

    queue, _ = _run(tmp_path, jobs)

    report = queue.get_jobs_report()
    assert (report.success, report.error) == (2, 0)
    assert child.exists()


def test_failing_job_with_a_limit_fails(tmp_path: Path) -> None:
    """A job which fails by itself (before the limit) is an error."""
    jobs = [
        {
            "timeout_seconds": 30,
            "function": DISPATCH,
            "parameters": {"cmd": ["false"]},
        },
    ]

    queue, _ = _run(tmp_path, jobs)

    assert queue.get_jobs_report().error == 1


@pytest.mark.parametrize("value", [0, -1])
def test_timeout_must_be_positive(value: float) -> None:
    """A zero or negative limit is rejected."""
    with pytest.raises(ValidationError):
        JobConfig.model_validate(
            {
                "function": "pyantz.jobs.testing.nop.do_nothing",
                "parameters": {},
                "timeout_seconds": value,
            },
        )
