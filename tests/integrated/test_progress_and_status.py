"""Test progress reports and the status command."""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING, Any

import pytest

from pyantz import start
from pyantz.status import describe_run
from pyantz.status import main as status_main

if TYPE_CHECKING:
    from pathlib import Path

DISPATCH = "pyantz.jobs.subproc.dispatch.dispatch"
NOP = "pyantz.jobs.testing.nop.do_nothing"


def _run(tmp_path: Path, jobs: list[dict[str, Any]], **submitter: Any) -> Path:  # noqa: ANN401
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
                **submitter,
            },
        },
    )
    return work


def _mixed_jobs() -> list[dict[str, Any]]:
    return [
        {"job_id": "good", "function": NOP, "parameters": {}},
        {"job_id": "bad", "function": DISPATCH, "parameters": {"cmd": ["false"]}},
        {
            "job_id": "blocked",
            "depends_on": ["bad"],
            "function": NOP,
            "parameters": {},
        },
    ]


def test_status_counts_match_the_queue(tmp_path: Path) -> None:
    """The summary of a finished run has the right counts and lists failures."""
    work = _run(tmp_path, _mixed_jobs())

    text = describe_run(work)

    assert "Jobs: 3" in text
    assert "succeeded: 1" in text
    assert "failed:    2" in text
    assert "running:   0" in text
    assert "Failed jobs:\n  bad\n  blocked" in text


def test_status_command_prints_the_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`pyantz-status <dir>` prints the same summary."""
    work = _run(tmp_path, _mixed_jobs())
    capsys.readouterr()  # drop what the jobs printed
    monkeypatch.setattr(sys, "argv", ["pyantz-status", os.fspath(work)])

    status_main()

    assert capsys.readouterr().out.strip() == describe_run(work)


def test_status_of_a_directory_without_a_run_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """There is a clear message and a failing status if no run is found."""
    monkeypatch.setattr(sys, "argv", ["pyantz-status", os.fspath(tmp_path)])

    with pytest.raises(SystemExit) as info:
        status_main()

    assert info.value.code == 1
    assert "No run found" in capsys.readouterr().err


def test_pool_logs_progress_while_running(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With worker processes, the parent reports progress regularly."""
    jobs = [
        {"job_id": "slow", "function": DISPATCH, "parameters": {"cmd": ["sleep", "3"]}},
        {"job_id": "quick", "function": NOP, "parameters": {}},
    ]

    with caplog.at_level(logging.INFO, logger="pyantz.infrastructure.runner.local"):
        _run(
            tmp_path,
            jobs,
            use_same_proc=False,
            number_processes=2,
            progress_interval=0.5,
        )

    progress = [r.getMessage() for r in caplog.records if "Progress:" in r.getMessage()]
    assert progress
    assert any("of 2 jobs done" in message for message in progress)
    assert any("1 succeeded" in message for message in progress)


def test_progress_can_be_turned_off(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """progress_interval=None means no reports."""
    jobs = [
        {"job_id": "slow", "function": DISPATCH, "parameters": {"cmd": ["sleep", "1"]}},
    ]

    with caplog.at_level(logging.INFO):
        _run(tmp_path, jobs, use_same_proc=False, progress_interval=None)

    assert "Progress:" not in caplog.text
