"""Test the SLURM runner explains what went wrong."""

import os
import sys
from typing import TYPE_CHECKING

import pytest

from pyantz.infrastructure.config.runners import SlurmRunnerConfig
from pyantz.infrastructure.runner.slurm import slurm_runner

if TYPE_CHECKING:
    from pathlib import Path


def test_submitting_outside_slurm_is_explained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Submitting child jobs outside of a slurm job says SLURM_JOB_ID is missing."""
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)

    with pytest.raises(RuntimeError, match="SLURM_JOB_ID"):
        slurm_runner._create_job_submitter(  # noqa: SLF001
            SlurmRunnerConfig(working_dir=tmp_path),
            tmp_path / "slurm_config.json",
        )


def test_missing_slurm_config_file_is_named(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing slurm config file is named in the error."""
    missing = tmp_path / "missing_config.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "-i", os.fspath(missing), "-c", "job.json"],
    )

    with pytest.raises(ValueError, match=r"missing_config\.json"):
        slurm_runner._load_job_config()  # noqa: SLF001


def test_missing_job_config_file_is_named(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing job config file is named in the error."""
    slurm_config = tmp_path / "slurm_config.json"
    slurm_config.write_text(SlurmRunnerConfig(working_dir=tmp_path).model_dump_json())
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "-i", os.fspath(slurm_config), "-c", "no_such_job.json"],
    )

    with pytest.raises(ValueError, match=r"no_such_job\.json"):
        slurm_runner._load_job_config()  # noqa: SLF001


def test_dangling_dependency_argument_is_explained() -> None:
    """`--dependency` with no value says so."""
    with pytest.raises(ValueError, match="without a value"):
        slurm_runner._add_dependency_to_sbatch(["--dependency"], ["1"])  # noqa: SLF001
