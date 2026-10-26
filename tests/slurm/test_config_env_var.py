"""Test the environment variable carrying the saved slurm config."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.config.runners import SlurmRunnerConfig
from pyantz.infrastructure.runner.slurm import start

NOP = "pyantz.jobs.testing.nop.do_nothing"
ENV_VAR = "PYANTZ_SLURM_CONFIG_FILE"


@pytest.fixture
def submitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run the slurm submitter against a mocked sbatch; returns the working dir."""

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:  # noqa: ANN401
        return subprocess.CompletedProcess(cmd, 0, b"1001\n")

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.delenv("PYANTZ_SLURM_CONFIG_DIR", raising=False)
    work = tmp_path / "work"
    work.mkdir()
    config = InitialConfig.model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}}],
            "submitter": {"type_": "slurm_sbatch", "working_dir": os.fspath(work)},
        },
    )
    start(config)
    return work


def test_variable_names_the_saved_config_file(submitted: Path) -> None:
    """The variable is named for what it holds: a file, inside the working dir."""
    saved = os.environ[ENV_VAR]

    assert os.path.isfile(saved)  # noqa: PTH113
    assert os.path.dirname(saved) == os.fspath(submitted)  # noqa: PTH120
    assert "PYANTZ_SLURM_CONFIG_DIR" not in os.environ


def test_saved_config_can_be_read_back_through_the_variable(submitted: Path) -> None:
    """The file the variable points to holds the slurm runner configuration."""
    loaded = SlurmRunnerConfig.model_validate_json(
        Path(os.environ[ENV_VAR]).read_text(encoding="utf-8"),
    )

    assert loaded.working_dir == submitted
    assert loaded.type_ == "slurm_sbatch"
