"""Test the slurm runner against a fake sbatch/squeue/scontrol (no slurm needed)."""

import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest

from pyantz.infrastructure.config import InitialConfig, JobWithContext
from pyantz.infrastructure.config.runners import SlurmRunnerConfig
from pyantz.infrastructure.runner.slurm import slurm_runner
from pyantz.infrastructure.runner.slurm.slurm_runner import (
    _add_dependency,
    _create_job_submitter,
    _initial_submit,
    _run_on_node,
)

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"
FAIL = "pyantz.jobs.testing.touch_file.touch_file"


class FakeSlurm:
    """Records the commands run and answers like sbatch, squeue and scontrol."""

    def __init__(self, squeue_output: str = "") -> None:
        """Create the fake; `squeue_output` is what every squeue prints."""
        self.commands: list[list[str]] = []
        self.squeue_output = squeue_output

    def run(self, cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:  # noqa: ANN401
        """Pretend to run the command."""
        sbatch_count = len(self.sbatch)
        self.commands.append(list(cmd))
        if cmd[0] == "sbatch":
            return subprocess.CompletedProcess(
                cmd, 0, f"{1000 + sbatch_count}\n".encode()
            )
        if cmd[0] == "squeue":
            return subprocess.CompletedProcess(cmd, 0, self.squeue_output.encode())
        return subprocess.CompletedProcess(cmd, 0, b"")

    @property
    def sbatch(self) -> list[list[str]]:
        """The sbatch commands run so far."""
        return [cmd for cmd in self.commands if cmd[0] == "sbatch"]

    @property
    def scontrol(self) -> list[list[str]]:
        """The scontrol commands run so far."""
        return [cmd for cmd in self.commands if cmd[0] == "scontrol"]


@pytest.fixture
def slurm(monkeypatch: pytest.MonkeyPatch) -> FakeSlurm:
    """Replace subprocess.run with a fake slurm, outside of any slurm job."""
    fake = FakeSlurm()
    monkeypatch.setattr(subprocess, "run", fake.run)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    return fake


def _config(work: Path, jobs: list[dict[str, Any]], **runner: Any) -> InitialConfig:  # noqa: ANN401
    work.mkdir(exist_ok=True)
    return InitialConfig.model_validate(
        {
            "jobs": jobs,
            "submitter": {
                "type_": "slurm_sbatch",
                "working_dir": os.fspath(work),
                **runner,
            },
        }
    )


def _job(job_id: str, *depends_on: str) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "function": NOP,
        "parameters": {},
        "depends_on": list(depends_on) or None,
    }


def _submit(config: InitialConfig) -> None:
    runner_config = config.submitter
    assert isinstance(runner_config, SlurmRunnerConfig)
    _initial_submit(config, runner_config, runner_config.working_dir / "slurm.json")


def _dependency_of(sbatch: list[str]) -> str | None:
    found = [arg for arg in sbatch if arg.startswith("--dependency=")]
    return found[0].removeprefix("--dependency=") if found else None


def _job_file(sbatch: list[str], work: Path) -> JobWithContext:
    path = work / sbatch[sbatch.index("-c") + 1]
    return JobWithContext.model_validate_json(path.read_text(encoding="utf-8"))


def test_initial_submit_orders_by_dependencies(
    tmp_path: Path, slurm: FakeSlurm
) -> None:
    """Dependencies are submitted first and referred to by their slurm ids."""
    work = tmp_path / "work"
    # listed in an order which is not a valid submission order
    config = _config(
        work, [_job("d", "b", "c"), _job("b", "a"), _job("c", "a"), _job("a")]
    )

    _submit(config)

    ids = [_job_file(cmd, work).job_id for cmd in slurm.sbatch]
    assert ids[0] == "a"
    assert ids[-1] == "d"
    slurm_id = {job_id: str(1000 + i) for i, job_id in enumerate(ids)}
    deps = {_job_file(cmd, work).job_id: _dependency_of(cmd) for cmd in slurm.sbatch}
    assert deps["a"] is None
    assert deps["b"] == f"afterok:{slurm_id['a']}"
    assert deps["c"] == f"afterok:{slurm_id['a']}"
    assert sorted((deps["d"] or "").split(",")) == sorted(
        [f"afterok:{slurm_id['b']}", f"afterok:{slurm_id['c']}"]
    )


def test_initial_submit_passes_user_arguments(tmp_path: Path, slurm: FakeSlurm) -> None:
    """The user's sbatch arguments, a time limit and --parsable are used."""
    config = _config(tmp_path / "work", [_job("a")], slurm_args=["--partition", "gpu"])

    _submit(config)

    cmd = slurm.sbatch[0]
    assert cmd[cmd.index("--partition") + 1] == "gpu"
    assert "--parsable" in cmd
    assert any(arg.startswith("--time=") for arg in cmd)
    assert cmd[cmd.index(sys.executable) + 1 :][:2] == [
        "-m",
        slurm_runner.ENTRY_MODULE_NAME,
    ]


def test_add_dependency_replaces_each_dependency_list(slurm: FakeSlurm) -> None:
    """Scontrol gets the whole new list for each job which waits on the parent."""
    _add_dependency("9", {"20": ["5"], "21": ["5", "6"]})

    assert slurm.scontrol == [
        ["scontrol", "update", "JobId=20", "Dependency=afterok:5,afterok:9"],
        ["scontrol", "update", "JobId=21", "Dependency=afterok:5,afterok:6,afterok:9"],
    ]


def test_submitting_from_a_node_inherits_dependencies(
    tmp_path: Path, slurm: FakeSlurm, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child job gets the node's job as a dependency, and its dependents wait."""
    monkeypatch.setenv("SLURM_JOB_ID", "100")
    slurm.squeue_output = "300|afterok:100(unfulfilled)\n301|(null)\n"
    runner_config = _config(tmp_path / "work", [_job("a")]).submitter
    assert isinstance(runner_config, SlurmRunnerConfig)

    submit = _create_job_submitter(runner_config, tmp_path / "slurm.json")
    submit(JobWithContext.model_validate(_job("x") | {"job_id": "x"}))
    submit(JobWithContext.model_validate(_job("y") | {"job_id": "y"}))

    assert [_dependency_of(cmd) for cmd in slurm.sbatch] == ["afterok:100"] * 2
    # the waiting job (300) must wait on every child: the 2nd update has both
    assert slurm.scontrol == [
        ["scontrol", "update", "JobId=300", "Dependency=afterok:100,afterok:1000"],
        [
            "scontrol",
            "update",
            "JobId=300",
            "Dependency=afterok:100,afterok:1000,afterok:1001",
        ],
    ]


def test_submitting_outside_of_slurm_is_an_error(
    tmp_path: Path, slurm: FakeSlurm
) -> None:
    """Jobs can only be submitted from within a slurm job."""
    runner_config = _config(tmp_path / "work", [_job("a")]).submitter
    assert isinstance(runner_config, SlurmRunnerConfig)

    with pytest.raises(RuntimeError, match="SLURM_JOB_ID"):
        _create_job_submitter(runner_config, tmp_path / "slurm.json")
    assert not slurm.commands


def _node_job(
    tmp_path: Path,
    function: str,
    parameters: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Write the files an sbatch-ed job reads and point the arguments at them."""
    config = _config(tmp_path / "work", [_job("a")])
    runner_config = config.submitter
    assert isinstance(runner_config, SlurmRunnerConfig)
    slurm_config = runner_config.working_dir / "slurm.json"
    slurm_config.write_text(runner_config.model_dump_json())
    job_file = runner_config.working_dir / "job.json"
    job = {"job_id": "a", "function": function, "parameters": parameters}
    job_file.write_text(JobWithContext.model_validate(job).model_dump_json())
    monkeypatch.setattr(
        sys, "argv", ["child", "-i", os.fspath(slurm_config), "-c", "job.json"]
    )
    monkeypatch.setenv("SLURM_JOB_ID", "100")


def test_run_on_node_succeeds(
    tmp_path: Path, slurm: FakeSlurm, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job which works makes the node's run succeed (exit status 0)."""
    _node_job(tmp_path, NOP, {}, monkeypatch)

    assert _run_on_node() is True
    assert not slurm.sbatch


def test_run_on_node_reports_failure(
    tmp_path: Path, slurm: FakeSlurm, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job which fails makes the run fail, so afterok dependents never run."""
    existing = tmp_path / "exists.txt"
    existing.touch()
    _node_job(
        tmp_path, FAIL, {"path": os.fspath(existing), "exist_ok": False}, monkeypatch
    )

    assert _run_on_node() is False
    assert not slurm.sbatch
