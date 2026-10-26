"""Test the command line entry point."""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.__main__ import main

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"
TOUCH = "pyantz.jobs.testing.touch_file.touch_file"


def _config(work: Path, touched: Path | None = None) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = [
        {"job_id": "first", "function": NOP, "parameters": {}, "name": "start"},
    ]
    if touched is not None:
        jobs.append(
            {
                "job_id": "second",
                "depends_on": ["first"],
                "function": TOUCH,
                "parameters": {"path": os.fspath(touched)},
            },
        )
    return {
        "jobs": jobs,
        "submitter": {
            "type_": "local_proc",
            "use_same_proc": True,
            "working_directory": os.fspath(work),
        },
    }


def _run_main(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["pyantz", *args])
    main()


def test_yaml_configuration_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A .yaml file is read like a json one."""
    touched = tmp_path / "touched"
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "jobs:\n"
        "  - job_id: first\n"
        f"    function: {NOP}\n"
        "    parameters: {}\n"
        "  - job_id: second\n"
        "    depends_on: [first]\n"
        f"    function: {TOUCH}\n"
        f"    parameters: {{path: {touched}}}\n"
        "submitter:\n"
        "  type_: local_proc\n"
        "  use_same_proc: true\n"
        f"  working_directory: {tmp_path / 'work'}\n",
    )

    _run_main(monkeypatch, os.fspath(config_file))

    assert touched.exists()


def test_json_configuration_still_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON keeps working."""
    touched = tmp_path / "touched"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(_config(tmp_path / "work", touched)))

    _run_main(monkeypatch, os.fspath(config_file))

    assert touched.exists()


def test_validate_prints_the_jobs_and_runs_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate on a good config lists jobs and dependencies without running."""
    touched = tmp_path / "touched"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(_config(tmp_path / "work", touched)))

    _run_main(monkeypatch, os.fspath(config_file), "--validate")

    output = capsys.readouterr().out
    assert "2 job(s)" in output
    assert "first (start)" in output
    assert "second <- first" in output
    assert not touched.exists()
    assert not (tmp_path / "work").exists()


def test_validate_reports_a_bad_config_and_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate on a config with an unknown function exits with status 1."""
    config = _config(tmp_path / "work")
    config["jobs"][0]["function"] = "no.such.module.function"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    with pytest.raises(SystemExit) as info:
        _run_main(monkeypatch, os.fspath(config_file), "--validate")

    assert info.value.code == 1
    assert "Invalid configuration" in capsys.readouterr().err


def test_invalid_syntax_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Text that isn't json is a failure with status 1, not a traceback."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{not json")

    with pytest.raises(SystemExit) as info:
        _run_main(monkeypatch, os.fspath(config_file))

    assert info.value.code == 1


def test_missing_file_is_a_usage_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A path that doesn't exist exits with the usual usage status 2."""
    with pytest.raises(SystemExit) as info:
        _run_main(monkeypatch, os.fspath(tmp_path / "nope.json"))

    assert info.value.code == 2  # noqa: PLR2004
    assert "No such file" in capsys.readouterr().err


def test_log_level_and_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--log-level controls what is logged and --log-file also writes it to a file."""
    import logging  # noqa: PLC0415

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(_config(tmp_path / "work", tmp_path / "t")))
    log_file = tmp_path / "run.log"
    root = logging.getLogger()
    handlers_before = list(root.handlers)
    level_before = root.level

    try:
        _run_main(
            monkeypatch,
            os.fspath(config_file),
            "--log-level",
            "info",
            "--log-file",
            os.fspath(log_file),
        )
        for handler in root.handlers:
            handler.flush()
        assert "Running job first" in log_file.read_text()
    finally:
        for handler in list(root.handlers):
            if handler not in handlers_before:
                root.removeHandler(handler)
                handler.close()
        for handler in handlers_before:
            if handler not in root.handlers:
                root.addHandler(handler)
        root.setLevel(level_before)
