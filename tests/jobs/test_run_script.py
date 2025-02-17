"""Test running a script"""

import os
import logging 

from pyantz.infrastructure.core.status import Status
from pyantz.jobs.run_script import run_script


logger = logging.getLogger("test")
logger.setLevel(0)

def test_run_script_fn(tmpdir) -> None:
    """Test running a script with the run_script fn"""

    script_content = """#!/bin/bash
    echo "hello"
    echo $1
    """

    script_path: str = os.path.join(tmpdir, "script.sh")
    stdout_file: str = os.path.join(tmpdir, "stdout.txt")

    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(script_content)
    os.chmod(script_path, 0o777)

    assert (
        run_script(
            {
                "script_path": script_path,
                "script_args": ["what?"],
                "stdout_save_file": stdout_file,
            }, logger
        )
        == Status.SUCCESS
    )

    assert os.path.exists(stdout_file)
    with open(stdout_file, "r", encoding="utf-8") as fh:
        results: str = fh.read()
    assert results == "hello\nwhat?\n"
