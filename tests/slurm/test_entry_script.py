"""Test how slurm child jobs are launched on the compute node."""

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.config.runners import SlurmRunnerConfig
from pyantz.infrastructure.runner.slurm import slurm_runner, start

if TYPE_CHECKING:
    import pytest

NOP = "pyantz.jobs.testing.nop.do_nothing"


def test_sbatch_command_uses_this_interpreter_and_module_form(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The job is run by `sys.executable -m <module>`, not a bare `python file`."""
    calls: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:  # noqa: ANN401
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, b"1001\n")

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    config = InitialConfig[SlurmRunnerConfig].model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}}],
            "submitter": {"type_": "slurm_sbatch", "working_dir": os.fspath(tmp_path)},
        },
    )

    start(config)

    (cmd,) = calls
    script = cmd.index(os.fspath(slurm_runner.ENTRY_BASH_FILE_PATH))
    assert cmd[script + 1 : script + 4] == [
        sys.executable,
        "-m",
        "pyantz.infrastructure.runner.slurm.slurm_runner",
    ]
    # the module named really is importable and is the one with the entry point
    module = importlib.import_module(cmd[script + 3])
    assert module.__file__ == slurm_runner.__file__


def test_run_script_keeps_arguments_intact() -> None:
    """Arguments with spaces and shell characters reach the command unchanged."""
    odd_args = ["path with spaces/file.json", "$HOME", "a;b", "*"]

    result = subprocess.run(
        [
            "bash",
            os.fspath(slurm_runner.ENTRY_BASH_FILE_PATH),
            sys.executable,
            "-c",
            "import json, sys; print(json.dumps(sys.argv[1:]))",
            *odd_args,
        ],
        capture_output=True,
        check=True,
    )

    assert result.stdout.decode().strip() == (
        '["path with spaces/file.json", "$HOME", "a;b", "*"]'
    )


def test_run_script_is_part_of_the_package() -> None:
    """The launcher script sits next to the module, so it is packaged with it."""
    script = Path(slurm_runner.__file__).parent / "run.sh"
    assert script.is_file()
    assert script == slurm_runner.ENTRY_BASH_FILE_PATH
