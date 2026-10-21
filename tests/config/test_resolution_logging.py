"""Test resolving parameters doesn't flood the info log."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from pyantz import start
from pyantz.infrastructure.config.variables import resolve_parameters

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_resolving_logs_nothing_at_info(caplog: pytest.LogCaptureFixture) -> None:
    """Resolving a job's parameters is a debug detail."""
    with caplog.at_level(logging.INFO, logger="pyantz.infrastructure.config.variables"):
        resolve_parameters({"a": "%{x}"}, {"x": 1})

    assert not caplog.records


def test_debug_log_still_available(caplog: pytest.LogCaptureFixture) -> None:
    """The message is still there for people debugging."""
    with caplog.at_level(
        logging.DEBUG, logger="pyantz.infrastructure.config.variables"
    ):
        resolve_parameters({"a": "%{x}"}, {"x": 1})

    assert "Resolving parameters" in caplog.text


def test_normal_run_has_no_resolution_messages_at_info(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A whole pipeline run doesn't log it for every job."""
    work = tmp_path / "work"
    work.mkdir()
    config = {
        "jobs": [
            {
                "function": "pyantz.jobs.testing.nop.do_nothing",
                "parameters": {},
            }
            for _ in range(3)
        ],
        "variables": {"v": 1},
        "submitter": {
            "type_": "local_proc",
            "use_same_proc": True,
            "working_directory": os.fspath(work),
        },
    }

    with caplog.at_level(logging.INFO):
        start(config)

    assert "Resolving parameters" not in caplog.text
