"""Test a pipeline that does nothing.

Pretty much just check syntax and whatnot, no logic checks really.
"""

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Final

from pyantz import start

MINIMAL_CONFIG: Final[dict[str, Any]] = {
    "jobs": [
        {
            "function": "pyantz.jobs.common.nop.do_nothing",
            "parameters": {
                "hello": "there",
                "general": "kenobi",
            },
        }
    ],
    "submitter": {
        "type_": "local_proc",
        # "working_directory" # set in test
    },
}


def test_doing_nothing_cli(tmp_path: Path) -> None:
    """Test running through the __main__ entry."""
    config = deepcopy(MINIMAL_CONFIG)
    config["submitter"]["working_directory"] = os.fspath(tmp_path)

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))

    subprocess.run(["python", "-m", "pyantz", os.fspath(config_path)], check=True)

def test_doing_nothing_direct_call(tmp_path: Path) -> None:
    """Test running through an imported function."""
    config = deepcopy(MINIMAL_CONFIG)
    config["submitter"]["working_directory"] = os.fspath(tmp_path)

    start(config) # type: ignore[arg-type]
