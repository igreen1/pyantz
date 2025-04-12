"""Test running the main entry script with `run.py`"""

import os
import subprocess

from pyantz.infrastructure.config.base import (
    InitialConfig,
)


def test_run_py(tmpdir) -> None:
    """Use make dirs job as an example to test the run script"""

    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": True}

    job_config = {
        "type": "job",
        "parameters": parameters,
        "function": "pyantz.jobs.file.make_dirs.make_dirs",
    }

    test_config = InitialConfig.model_validate(
        {
            "submitter_config": {"type": "local"},
            "analysis_config": {
                "variables": {},
                "config": {"type": "pipeline", "stages": [job_config]},
            },
        }
    )
    cwd = os.path.dirname(os.path.normpath(__file__))
    repo_dir = os.path.abspath(os.path.join(cwd, os.pardir))
    print(repo_dir)
    config_path = os.fspath(os.path.join(tmpdir, "config.json"))

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(test_config.model_dump_json())

    subprocess.run(
        [
            "python",
            "src/pyantz/run.py",
            "--config",
            config_path,
        ],
        cwd=repo_dir,
        check=True,
    )

    assert os.path.exists(path)
