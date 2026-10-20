"""Test the approximately equal comparator of the if/else jobs."""

import os
from typing import TYPE_CHECKING, Any

import pytest

from pyantz import start

if TYPE_CHECKING:
    from pathlib import Path

TOUCH = "pyantz.jobs.testing.touch_file.touch_file"


def _run(tmp_path: Path, function: str, **parameters: Any) -> None:  # noqa: ANN401
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    branches: dict[str, Any] = {
        "if_true": {
            "function": TOUCH,
            "parameters": {"path": os.fspath(tmp_path / "IF")},
        },
    }
    if function.endswith("if_else"):
        branches["if_false"] = {
            "function": TOUCH,
            "parameters": {"path": os.fspath(tmp_path / "ELSE")},
        }
    start(
        {
            "jobs": [
                {
                    "function": function,
                    "parameters": {"comparator": "~=", **parameters, **branches},
                },
            ],
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": True,
                "working_directory": os.fspath(work),
            },
        },
    )


IF_ELSE = "pyantz.jobs.branching.if_else.if_else"
CONDITIONAL = "pyantz.jobs.branching.if_else.conditionally_execute"


def test_close_values_take_the_true_branch(tmp_path: Path) -> None:
    """1.0000001 is approximately 1.0."""
    _run(tmp_path, IF_ELSE, left_side=1.0000001, right_side=1.0)

    assert (tmp_path / "IF").exists()
    assert not (tmp_path / "ELSE").exists()


def test_distant_values_take_the_false_branch(tmp_path: Path) -> None:
    """1.1 is not approximately 1.0 (and `~=` is no longer plain inequality)."""
    _run(tmp_path, IF_ELSE, left_side=1.1, right_side=1.0)

    assert (tmp_path / "ELSE").exists()
    assert not (tmp_path / "IF").exists()


def test_equal_values_are_approximately_equal(tmp_path: Path) -> None:
    """Equal values take the true branch (they would not with `!=`)."""
    _run(tmp_path, IF_ELSE, left_side=5, right_side=5)

    assert (tmp_path / "IF").exists()


def test_tolerances_can_be_set(tmp_path: Path) -> None:
    """abs_tol widens what counts as close."""
    _run(tmp_path, IF_ELSE, left_side=100, right_side=103, abs_tol=5)

    assert (tmp_path / "IF").exists()


def test_numeric_strings_are_read_as_numbers(tmp_path: Path) -> None:
    """Values that arrive as text still compare numerically."""
    _run(tmp_path, IF_ELSE, left_side="2.0000001", right_side="2")

    assert (tmp_path / "IF").exists()


def test_non_numbers_are_never_close(tmp_path: Path) -> None:
    """Text which isn't a number takes the false branch rather than crashing."""
    _run(tmp_path, IF_ELSE, left_side="abc", right_side="abd")

    assert (tmp_path / "ELSE").exists()


@pytest.mark.parametrize(("right", "created"), [(1.0, True), (2.0, False)])
def test_conditional_execution_uses_it_too(
    tmp_path: Path,
    right: float,
    created: bool,  # noqa: FBT001
) -> None:
    """conditionally_execute understands `~=` as well."""
    _run(tmp_path, CONDITIONAL, left_side=1.0000001, right_side=right)

    assert (tmp_path / "IF").exists() is created
