"""Run the typescript of the frontend with node, as the tests of it need."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

FRONTEND = Path(__file__).parents[2] / "frontend" / "pyantz"

# node runs typescript directly (it strips the types) from this version on
MIN_NODE = (22, 18)


def _node_version() -> tuple[int, ...] | None:
    node = shutil.which("node")
    if node is None:
        return None
    out = subprocess.run(
        [node, "--version"], capture_output=True, text=True, check=True
    ).stdout
    found = re.match(r"v(\d+)\.(\d+)", out)
    return (int(found[1]), int(found[2])) if found else None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark the tests of this directory as the ones which need the frontend."""
    for item in items:
        if Path(str(item.fspath)).parent == Path(__file__).parent:
            item.add_marker(pytest.mark.frontend)


@pytest.fixture
def needs_node() -> None:
    """Skip the test when node can't run typescript."""
    version = _node_version()
    if version is None:
        pytest.skip("node is not installed")
    if version < MIN_NODE:
        pytest.skip(f"node {MIN_NODE} or later is needed")


@pytest.fixture
def run_script() -> Any:  # noqa: ANN401
    """Run a script of the frontend, and return what it printed."""

    def run(script: str, *args: str) -> str:
        result = subprocess.run(
            ["node", f"scripts/{script}", *args],
            cwd=FRONTEND,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    return run


@pytest.fixture
def model_fields(run_script: Any, needs_node: None) -> dict[str, list[str]]:  # noqa: ANN401, ARG001
    """Get the fields of the config models, as the frontend knows them."""
    return json.loads(run_script("dump_model_fields.ts"))
