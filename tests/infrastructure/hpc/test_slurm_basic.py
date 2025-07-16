"""Test runnign on the slurm grid"""

import os
import shutil
import time

import pytest

import pyantz.run

HAS_SBATCH: bool = shutil.which("sbatch") is not None


@pytest.mark.skipif(not HAS_SBATCH, reason="Requies `sbatch` command to run")
def test_submitting_to_sbatch(tmpdir) -> None:
    dst_file = os.path.join(tmpdir, "end.txt")

    src_file = os.path.join(tmpdir, "start.txt")

    test_text: str = "Hello there general kenobi"

    with open(src_file, "w", encoding="utf-8") as fh:
        fh.write(test_text)

    test_config = {
        "submitter_config": {
            "type": "slurm_basic",
            "working_directory": os.fspath(tmpdir),
        },
        "analysis_config": {
            "variables": {},
            "config": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "function": "pyantz.jobs.file.copy.copy",
                        "parameters": {
                            "source": os.fspath(src_file),
                            "destination": os.fspath(dst_file),
                        },
                    },
                    {
                        "type": "job",
                        "function": "pyantz.jobs.file.delete.delete",
                        "parameters": {
                            "path": os.fspath(src_file),
                        },
                    },
                ],
            },
        },
    }

    pyantz.run.run(test_config)

    assert os.path.exists(dst_file)
    with open(dst_file, "r", encoding="utf-8") as fh:
        ret = fh.read()
    assert ret == test_text

    time_to_wait_s: int = 3
    time_per_cycle: float = 0.1
    count: int = 0
    while os.path.exists(src_file):
        time.sleep(time_per_cycle)
        count += 1
        if count * time_per_cycle > time_to_wait_s:
            assert not os.path.exists(src_file)

    assert not os.path.exists(src_file)
