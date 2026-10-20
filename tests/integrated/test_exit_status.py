"""Test that the outcome of a pipeline is reported to the caller."""

import json
import os
import sys
from typing import TYPE_CHECKING, Any

import pytest

from pyantz import start
from pyantz.__main__ import main

if TYPE_CHECKING:
    from pathlib import Path


def _config(tmp_path: Path, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    return {
        "jobs": jobs,
        "submitter": {"type_": "local_proc", "working_directory": os.fspath(work)},
    }


def _ok_job() -> dict[str, Any]:
    return {"function": "pyantz.jobs.testing.nop.do_nothing", "parameters": {}}


def _failing_job(tmp_path: Path) -> dict[str, Any]:
    """Touching an existing file with exist_ok=False makes the job return False."""
    existing = tmp_path / "exists.txt"
    existing.touch()
    return {
        "function": "pyantz.jobs.testing.touch_file.touch_file",
        "parameters": {"path": os.fspath(existing), "exist_ok": False},
    }


def _run_main(
    tmp_path: Path,
    config: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    monkeypatch.setattr(sys, "argv", ["pyantz", os.fspath(config_file)])
    main()


def test_start_reports_success(tmp_path: Path) -> None:
    """`start` returns a report of a fully successful run."""
    report = start(_config(tmp_path, [_ok_job()]))

    assert report is not None
    assert report.all_succeeded
    assert report.success == report.total == 1


def test_start_reports_failure(tmp_path: Path) -> None:
    """`start` returns a report which includes the failed job."""
    report = start(_config(tmp_path, [_ok_job(), _failing_job(tmp_path)]))

    assert report is not None
    assert not report.all_succeeded
    assert report.error == 1
    assert report.success == 1


def test_main_exits_nonzero_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI exits with status 1 when a job failed."""
    with pytest.raises(SystemExit) as exc_info:
        _run_main(tmp_path, _config(tmp_path, [_failing_job(tmp_path)]), monkeypatch)
    assert exc_info.value.code == 1


def test_main_exits_zero_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI returns normally (exit status 0) when every job succeeded."""
    _run_main(tmp_path, _config(tmp_path, [_ok_job()]), monkeypatch)
