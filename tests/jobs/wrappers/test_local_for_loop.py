"""Test the local for loop stops at the first failure."""

from typing import TYPE_CHECKING, Any

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.runner.job_manager import run_job
from pyantz.jobs.wrappers.loops import local_for_loop  # noqa: F401  (registers the job)

if TYPE_CHECKING:
    from pathlib import Path

LOOP = "pyantz.jobs.wrappers.loops.local_for_loop"
DISPATCH = "pyantz.jobs.subproc.dispatch.dispatch"


def _append(path: Path, text: str) -> dict[str, Any]:
    """Job which appends a line to the file."""
    return {
        "function": DISPATCH,
        "parameters": {"cmd": ["sh", "-c", f'echo {text} >> "{path}"']},
    }


def _fail() -> dict[str, Any]:
    return {"function": DISPATCH, "parameters": {"cmd": ["false"]}}


def _run_loop(iterations: int, jobs: list[dict[str, Any]]) -> bool:
    loop = JobWithContext.model_validate(
        {
            "function": LOOP,
            "parameters": {"num_iterations": iterations, "jobs": jobs},
        },
    )
    return run_job(loop, lambda *_: None)


def _lines(path: Path) -> list[str]:
    return path.read_text().split() if path.exists() else []


def test_failure_in_second_job_stops_all_iterations(tmp_path: Path) -> None:
    """With a failing second job, the first job ran exactly once."""
    log = tmp_path / "log.txt"

    assert (
        _run_loop(3, [_append(log, "first"), _fail(), _append(log, "third")]) is False
    )

    assert _lines(log) == ["first"]


def test_failure_in_first_job_runs_nothing_else(tmp_path: Path) -> None:
    """If the first job fails, no other job of any iteration runs."""
    log = tmp_path / "log.txt"

    assert _run_loop(3, [_fail(), _append(log, "second")]) is False

    assert not log.exists()


def test_failure_in_a_later_iteration_stops_the_loop(tmp_path: Path) -> None:
    """A job which only fails the second time round stops the remaining iterations."""
    log = tmp_path / "log.txt"
    marker = tmp_path / "marker"
    # fails when the marker exists (i.e. from the second iteration on)
    fail_second_time = {
        "function": DISPATCH,
        "parameters": {
            "cmd": ["sh", "-c", f'test ! -e "{marker}" && touch "{marker}"'],
        },
    }

    assert _run_loop(5, [_append(log, "a"), fail_second_time]) is False

    assert _lines(log) == ["a", "a"]


def test_successful_loop_runs_every_iteration(tmp_path: Path) -> None:
    """Without failures every job runs on every iteration."""
    log = tmp_path / "log.txt"

    assert _run_loop(3, [_append(log, "x"), _append(log, "y")]) is True

    assert _lines(log) == ["x", "y"] * 3


def test_zero_iterations_succeeds() -> None:
    """An empty loop is a success and runs nothing."""
    assert _run_loop(0, [_fail()]) is True
