"""What the editor exports is a config which pyantz accepts and runs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from pyantz import start
from pyantz.infrastructure.config import InitialConfig

GRAPH = Path(__file__).parent / "graph.json"
UI_KEY = "x-pyantz-ui"


def _export(run_script: Any, tmp_path: Path, *args: str) -> dict[str, Any]:  # noqa: ANN401
    """Export the graph of the fixture, with its files in `tmp_path`."""
    graph = tmp_path / "graph.json"
    # as_posix: a "\\" of a Windows path would be an escape in the json
    graph.write_text(GRAPH.read_text().replace("%TMP%", tmp_path.as_posix()))
    config: dict[str, Any] = json.loads(
        run_script("graph_to_config.ts", str(graph), *args)
    )
    return config


def test_the_export_has_the_dependencies(
    run_script: Any,  # noqa: ANN401
    needs_node: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    """Edges become ``depends_on``, and nested jobs stay nested."""
    config = _export(run_script, tmp_path)

    first, second, wrapper = config["jobs"]
    assert "depends_on" not in first
    assert second["depends_on"] == ["first"]
    assert re.fullmatch(r"n1|first", first["job_id"])
    assert wrapper["depends_on"] == [second["job_id"]]
    assert wrapper["parameters"]["jobs"][0]["job_id"] == "inside"


def test_the_export_runs(
    run_script: Any,  # noqa: ANN401
    needs_node: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    """The jobs all run, which they only do if the dependencies were understood."""
    config = _export(run_script, tmp_path)

    start(config)

    assert (tmp_path / "first.txt").read_text() == "one"
    assert (tmp_path / "second.txt").read_text() == "two"
    assert (tmp_path / "inside.txt").read_text() == "three"


def test_the_export_with_layout_is_still_accepted(
    run_script: Any,  # noqa: ANN401
    needs_node: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    """The positions of the jobs are in the config, and pyantz ignores them (D5)."""
    config = _export(run_script, tmp_path, "--layout")

    assert set(config[UI_KEY]["positions"]) == {
        "jobs.0",
        "jobs.1",
        "jobs.2",
        "jobs.2.parameters.jobs.0",
    }
    InitialConfig.model_validate(config)
    start(config)
    assert (tmp_path / "inside.txt").exists()


@pytest.mark.parametrize("extra", [{UI_KEY: {"positions": {}}}, {"notes": "anything"}])
def test_unknown_keys_of_a_config_are_ignored(extra: dict[str, Any]) -> None:
    """The editor keeps keys it does not know, and adds ``x-pyantz-ui``.

    This pins that the config accepts them: if it ever forbids extra keys, the
    editor's exports stop working and its layout key needs another home.
    """
    config = {
        "submitter": {"type_": "local_proc", "working_directory": "w"},
        "jobs": [{"function": "pyantz.jobs.testing.nop.do_nothing", "parameters": {}}],
        **extra,
    }

    InitialConfig.model_validate(config)
