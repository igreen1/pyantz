"""Test the jobs which run a sub-pipeline with another submitter or host."""

import os
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from pyantz import start
from pyantz.jobs.wrappers.submit import HostParams, SubmitParams

if TYPE_CHECKING:
    from pathlib import Path

SUBMIT = "pyantz.jobs.wrappers.submit.submit"
NEW_HOST = "pyantz.jobs.wrappers.submit.new_host"
TOUCH = "pyantz.jobs.testing.touch_file.touch_file"


def _runner(work: Path) -> dict[str, Any]:
    work.mkdir(exist_ok=True)
    return {
        "type_": "local_proc",
        "use_same_proc": True,
        "poll_timeout": 0.01,
        "working_directory": os.fspath(work),
    }


def _run(tmp_path: Path, job: dict[str, Any], **extra: Any) -> None:  # noqa: ANN401
    start(
        {
            "jobs": [job],
            "submitter": _runner(tmp_path / "outer_work"),
            **extra,
        },
    )


def test_submit_runs_the_jobs_with_its_own_runner(tmp_path: Path) -> None:
    """The sub-pipeline runs, in the working directory of the new runner."""
    inner_work = tmp_path / "inner_work"
    produced = tmp_path / "produced"
    job = {
        "function": SUBMIT,
        "parameters": {
            "runner_config": _runner(inner_work),
            "jobs": [
                {"function": TOUCH, "parameters": {"path": os.fspath(produced)}},
            ],
        },
    }

    _run(tmp_path, job)

    assert produced.exists()
    assert (inner_work / "queue.db").exists()  # the inner pipeline had its own queue


def test_submit_passes_variables_down(tmp_path: Path) -> None:
    """Variables of the outer pipeline are visible to the inner jobs."""
    job = {
        "function": SUBMIT,
        "parameters": {
            "runner_config": _runner(tmp_path / "inner_work"),
            "jobs": [
                {
                    "function": TOUCH,
                    "parameters": {
                        "path": os.fspath(tmp_path / "produced_%{greeting}")
                    },
                },
            ],
        },
    }

    _run(tmp_path, job, variables={"greeting": "hello"})

    assert (tmp_path / "produced_hello").exists()


def test_inner_jobs_with_dependencies_all_run(tmp_path: Path) -> None:
    """The jobs of the sub-pipeline, with their dependencies, all run."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    job = {
        "function": SUBMIT,
        "parameters": {
            "runner_config": _runner(tmp_path / "inner_work"),
            "jobs": [
                {
                    "job_id": "one",
                    "function": TOUCH,
                    "parameters": {"path": os.fspath(first)},
                },
                {
                    "job_id": "two",
                    "depends_on": ["one"],
                    "function": TOUCH,
                    "parameters": {"path": os.fspath(second)},
                },
            ],
        },
    }

    _run(tmp_path, job)

    assert first.exists()
    assert second.exists()


def test_new_host_with_a_local_host_runs_the_jobs(tmp_path: Path) -> None:
    """A `local` host is the same machine, with the new submitter."""
    produced = tmp_path / "produced"
    job = {
        "function": NEW_HOST,
        "parameters": {
            "host_config": {"type_": "local"},
            "submit_config": _runner(tmp_path / "inner_work"),
            "jobs": [
                {"function": TOUCH, "parameters": {"path": os.fspath(produced)}},
            ],
        },
    }

    _run(tmp_path, job)

    assert produced.exists()


def test_runner_config_is_chosen_by_its_type(tmp_path: Path) -> None:
    """A slurm runner config becomes a slurm config, others are rejected."""
    slurm_dir = tmp_path / "slurm"
    slurm_dir.mkdir()

    params = SubmitParams.model_validate(
        {
            "runner_config": {"type_": "slurm_sbatch", "working_dir": str(slurm_dir)},
            "jobs": [],
        },
    )

    assert params.runner_config.type_ == "slurm_sbatch"
    with pytest.raises(ValidationError):
        SubmitParams.model_validate(
            {"runner_config": {"type_": "carrier_pigeon"}, "jobs": []},
        )


def test_host_params_pick_the_host_class_by_type() -> None:
    """The host type selects ssh / container."""
    runner = {"type_": "local_proc", "working_directory": "."}
    ssh = HostParams.model_validate(
        {
            "host_config": {"type_": "ssh", "remote_host": "h"},
            "submit_config": runner,
            "jobs": [],
        },
    )
    container = HostParams.model_validate(
        {"host_config": {"type_": "container"}, "submit_config": runner, "jobs": []},
    )

    assert ssh.host_config.type_ == "ssh"
    assert container.host_config.type_ == "container"
