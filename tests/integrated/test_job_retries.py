"""Test failed jobs are retried the configured number of times."""

import os
from typing import TYPE_CHECKING, Any

from pyantz import start
from pyantz.infrastructure.distributed_queue.sql import SqliteQueue

if TYPE_CHECKING:
    from pathlib import Path

DISPATCH = "pyantz.jobs.subproc.dispatch.dispatch"
TOUCH = "pyantz.jobs.testing.touch_file.touch_file"


def _flaky(counter: Path, succeed_on_attempt: int, **extra: Any) -> dict[str, Any]:  # noqa: ANN401
    """Make a job which records every attempt and succeeds from a certain one."""
    script = (
        f'echo x >> "{counter}"; test "$(wc -l < "{counter}")" -ge {succeed_on_attempt}'
    )
    return {
        "function": DISPATCH,
        "parameters": {"cmd": ["sh", "-c", script]},
        **extra,
    }


def _run(tmp_path: Path, jobs: list[dict[str, Any]]) -> SqliteQueue:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
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
    return SqliteQueue(work / "queue.db")


def _attempts(counter: Path) -> int:
    return len(counter.read_text().split()) if counter.exists() else 0


def test_job_succeeding_on_the_second_try_ends_successfully(tmp_path: Path) -> None:
    """With max_retries=1 a job failing once ends as a success, and runs twice."""
    counter = tmp_path / "attempts"

    queue = _run(tmp_path, [_flaky(counter, 2, job_id="flaky", max_retries=1)])

    report = queue.get_jobs_report()
    assert (report.success, report.error) == (1, 0)
    assert _attempts(counter) == 2  # noqa: PLR2004


def test_without_retries_the_failure_is_final_and_dependents_fail(
    tmp_path: Path,
) -> None:
    """With max_retries=0 the job runs once and its dependents error."""
    counter = tmp_path / "attempts"
    after = tmp_path / "after"
    jobs = [
        _flaky(counter, 2, job_id="flaky"),
        {
            "job_id": "after",
            "depends_on": ["flaky"],
            "function": TOUCH,
            "parameters": {"path": os.fspath(after)},
        },
    ]

    queue = _run(tmp_path, jobs)

    report = queue.get_jobs_report()
    assert (report.success, report.error) == (0, 2)
    assert _attempts(counter) == 1
    assert not after.exists()


def test_dependents_wait_for_the_retry(tmp_path: Path) -> None:
    """A dependent runs only after the retried job finally succeeds."""
    counter = tmp_path / "attempts"
    after = tmp_path / "after"
    jobs = [
        _flaky(counter, 3, job_id="flaky", max_retries=2),
        {
            "job_id": "after",
            "depends_on": ["flaky"],
            "function": TOUCH,
            "parameters": {"path": os.fspath(after)},
        },
    ]

    queue = _run(tmp_path, jobs)

    assert queue.get_jobs_report().success == 2  # noqa: PLR2004
    assert _attempts(counter) == 3  # noqa: PLR2004
    assert after.exists()


def test_retries_are_limited(tmp_path: Path) -> None:
    """A job which always fails is attempted once plus max_retries times."""
    counter = tmp_path / "attempts"
    after = tmp_path / "after"
    jobs = [
        _flaky(counter, 100, job_id="never", max_retries=2),
        {
            "job_id": "after",
            "depends_on": ["never"],
            "function": TOUCH,
            "parameters": {"path": os.fspath(after)},
        },
    ]

    queue = _run(tmp_path, jobs)

    report = queue.get_jobs_report()
    assert report.error == 2  # noqa: PLR2004
    assert _attempts(counter) == 3  # noqa: PLR2004
    assert not after.exists()
