"""Test the slurm working directory is only required where slurm runs."""

import os
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.runner.slurm import start

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _config(working_dir: str, host: dict[str, Any]) -> dict[str, Any]:
    return {
        "jobs": [{"function": NOP, "parameters": {}}],
        "submitter": {"type_": "slurm_sbatch", "working_dir": working_dir},
        "host": host,
    }


def test_nonexistent_working_dir_valid_for_ssh_host() -> None:
    """A path that only exists on the cluster doesn't break local parsing."""
    config = InitialConfig.model_validate(
        _config(
            "/cluster/only/path",
            {"type_": "ssh", "remote_host": "login.cluster"},
        ),
    )
    assert os.fspath(config.submitter.working_dir) == "/cluster/only/path"


def test_start_errors_clearly_for_missing_working_dir(tmp_path: Path) -> None:
    """The slurm runner checks the directory where it actually runs."""
    missing = tmp_path / "missing"
    config = InitialConfig.model_validate(
        _config(os.fspath(missing), {"type_": "local"}),
    )

    with pytest.raises(NotADirectoryError, match="missing"):
        start(config)
