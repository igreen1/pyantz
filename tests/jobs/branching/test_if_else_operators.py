"""Test coercion and the extra operators of the if/else jobs."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import pytest

from pyantz import start
from pyantz.jobs.branching.if_else import IfElseParams, _compare

if TYPE_CHECKING:
    from pathlib import Path

TOUCH = "pyantz.jobs.testing.touch_file.touch_file"
NOP = "pyantz.jobs.testing.nop.do_nothing"


def _took_true_branch(tmp_path: Path, **parameters: Any) -> bool:  # noqa: ANN401
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    start(
        {
            "jobs": [
                {
                    "function": "pyantz.jobs.branching.if_else.if_else",
                    "parameters": {
                        **parameters,
                        "if_true": {
                            "function": TOUCH,
                            "parameters": {"path": os.fspath(tmp_path / "IF")},
                        },
                        "if_false": {
                            "function": TOUCH,
                            "parameters": {"path": os.fspath(tmp_path / "ELSE")},
                        },
                    },
                },
            ],
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": True,
                "working_directory": os.fspath(work),
            },
        },
    )
    took_true = (tmp_path / "IF").exists()
    assert took_true != (tmp_path / "ELSE").exists()
    return took_true


def _evaluate(left: Any, comparator: str, right: Any, coerce: str = "auto") -> bool:  # noqa: ANN401
    params = IfElseParams.model_validate(
        {
            "left_side": left,
            "right_side": right,
            "comparator": comparator,
            "coerce": coerce,
            "if_true": {"function": NOP, "parameters": {}},
            "if_false": {"function": NOP, "parameters": {}},
        },
    )
    return _compare(params)


def test_numeric_strings_compare_as_numbers_end_to_end(tmp_path: Path) -> None:
    """Text "10" is greater than "9" as numbers (as text it would not be)."""
    assert _took_true_branch(
        tmp_path,
        left_side="10",
        right_side="9",
        comparator=">",
    )


def test_regex_match_end_to_end(tmp_path: Path) -> None:
    """`=~` searches the left side for the pattern on the right."""
    assert _took_true_branch(
        tmp_path,
        left_side="run_42_done",
        right_side=r"_\d+_",
        comparator="=~",
    )


def test_membership_end_to_end(tmp_path: Path) -> None:
    """`not in` is true when the left text isn't in the right text."""
    assert _took_true_branch(
        tmp_path,
        left_side="x",
        right_side="abc",
        comparator="not in",
    )


@pytest.mark.parametrize(
    ("left", "comparator", "right", "coerce", "expected"),
    [
        ("10", ">", "9", "auto", True),
        ("10", ">", "9", "str", False),  # "10" < "9" as text
        ("10", ">", "9", "float", True),
        (10, ">", "9", "auto", True),
        ("abc", "<", "abd", "auto", True),
        ("abc", "<", 5, "auto", False),  # a number against text compares as text
        ("2.50", "==", 2.5, "auto", True),
        ("2.50", "==", "2.5", "str", False),
        ("nan", "==", "nan", "auto", True),  # not numbers, so compared as text
        ("ell", "in", "hello", "auto", True),
        ("xyz", "in", "hello", "auto", False),
        ("xyz", "not in", "hello", "auto", True),
        ("an", "in", "banana", "auto", True),
        ("^he", "=~", "hello", "auto", False),
        ("hello", "=~", "^he", "auto", True),
        ("hello", "=~", "^lo", "auto", False),
    ],
)
def test_comparisons(
    left: Any,  # noqa: ANN401
    comparator: str,
    right: Any,  # noqa: ANN401
    coerce: str,
    expected: bool,  # noqa: FBT001
) -> None:
    """Each operator and coercion mode gives the documented answer."""
    assert _evaluate(left, comparator, right, coerce) is expected


def test_float_coercion_rejects_text() -> None:
    """With coerce=float, something that isn't a number is an error."""
    with pytest.raises(ValueError, match="as numbers"):
        _evaluate("abc", "<", 3, "float")
