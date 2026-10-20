"""Test that variable substitution preserves the type of whole-value references."""

import os
from typing import TYPE_CHECKING, Any

from pyantz import start
from pyantz.infrastructure.config.variables import resolve_var_any

if TYPE_CHECKING:
    from pathlib import Path


def test_whole_value_reference_keeps_type() -> None:
    """A parameter that is exactly one reference gets the raw value."""
    variables = {"n": 5, "flag": True, "items": [1, 2], "conf": {"a": 1}}
    result, unresolved = resolve_var_any(
        {"n": "%{n}", "flag": "%{flag}", "items": "%{items}", "conf": "%{conf}"},
        variables,
    )
    assert result == variables
    assert isinstance(result["n"], int)
    assert not unresolved


def test_embedded_reference_is_interpolated() -> None:
    """References embedded in a larger string are still stringified."""
    result, unresolved = resolve_var_any(
        {"a": "x_%{n}", "b": "%{n}_y"},
        {"n": 5},
    )
    assert result == {"a": "x_5", "b": "5_y"}
    assert not unresolved


def test_unknown_reference_left_alone() -> None:
    """Unset variables remain in place and are flagged."""
    result, unresolved = resolve_var_any("%{missing}", {"n": 5})
    assert result == "%{missing}"
    assert unresolved


def _run_if_else(
    tmp_path: Path, left: str, comparator: str, variables: dict[str, Any]
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    config: dict[str, Any] = {
        "jobs": [
            {
                "function": "pyantz.jobs.branching.if_else.if_else",
                "parameters": {
                    "left_side": left,
                    "right_side": 9,
                    "comparator": comparator,
                    "if_true": {
                        "function": "pyantz.jobs.testing.touch_file.touch_file",
                        "parameters": {"path": os.fspath(tmp_path / "IF.txt")},
                    },
                    "if_false": {
                        "function": "pyantz.jobs.testing.touch_file.touch_file",
                        "parameters": {"path": os.fspath(tmp_path / "ELSE.txt")},
                    },
                },
            },
        ],
        "submitter": {"type_": "local_proc", "working_directory": os.fspath(work)},
        "variables": variables,
    }
    start(config)


def test_if_else_compares_numeric_variable(tmp_path: Path) -> None:
    """10 > 9 is true (a string comparison "10" > "9" would be false)."""
    _run_if_else(tmp_path, "%{a}", ">", {"a": 10})
    assert (tmp_path / "IF.txt").exists()
    assert not (tmp_path / "ELSE.txt").exists()


def test_if_else_numeric_variable_false_branch(tmp_path: Path) -> None:
    """8 > 9 is false and takes the else branch."""
    _run_if_else(tmp_path, "%{a}", ">", {"a": 8})
    assert (tmp_path / "ELSE.txt").exists()
    assert not (tmp_path / "IF.txt").exists()
