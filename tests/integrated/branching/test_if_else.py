"""Test branching with an if statement."""

from __future__ import annotations

import itertools
import random
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any


def make_if_job(p: Path) -> dict[str, Any]:
    """Make the job that runs if true."""
    return {
        "function": "pyantz.jobs.testing.touch_file",
        "parameters": {"path": p / "IF.txt"},
    }


def make_else_job(p: Path) -> dict[str, Any]:
    """Make the job that runs if false (not true!)."""
    return {
        "function": "pyantz.jobs.testing.touch_file",
        "parameters": {"path": p / "ELSE.txt"},
    }


def test_if_true(
    tmp_path: Path,
    run_integrated_jobs: Callable[[list[dict[str, Any]]], None],
) -> None:
    """Test taking the if branch."""
    conditional_parms = {
        "left_side": 1,
        "right_side": 2,
        "comparator": "<",
        "if_true": make_if_job(tmp_path),
        "if_false": make_else_job(tmp_path),
    }
    job = {
        "function": "pyantz.jobs.branching.if_else.if_else",
        "parameters": conditional_parms,
    }

    run_integrated_jobs([job])

    assert (tmp_path / "IF.txt").exists()


def test_if_false(
    tmp_path: Path,
    run_integrated_jobs: Callable[[list[dict[str, Any]]], None],
) -> None:
    """Test taking the if branch."""
    conditional_parms = {
        "left_side": 1,
        "right_side": 2,
        "comparator": ">",  # DIFFERENCE FROM OTHER JOB
        "if_true": make_if_job(tmp_path),
        "if_false": make_else_job(tmp_path),
    }
    job = {
        "function": "pyantz.jobs.branching.if_else.if_else",
        "parameters": conditional_parms,
    }

    run_integrated_jobs([job])

    assert (tmp_path / "ELSE.txt").exists()


SORTED_INTS: list[int] = sorted({random.randint(0, 1000) for _ in range(10)})  # noqa: S311


def opposite_ops(*not_ops: str) -> list[str]:
    """Get the other operations."""
    all_ops = [
        "=",
        "==",
        "<",
        "<=",
        ">",
        ">=",
        "!=",
        "~=",
    ]
    return list(set(all_ops) - set(not_ops))


TRUE_INT_COMPARISONS: list[tuple[int, str, int]] = [
    *[
        (val, op, val)
        for val in SORTED_INTS
        for op in (
            "=",
            "==",
            "<=",
            ">=",
        )
    ],
    *[
        (left, op, right)
        for left, right in itertools.pairwise(SORTED_INTS)
        for op in (
            "!=",
            "~=",
            "<",
            "<=",
        )
    ],
    *[
        (left, op, right)
        for left, right in zip(
            SORTED_INTS[1:],
            SORTED_INTS,
            strict=False,
        )
        for op in (
            ">",
            ">=",
        )
    ],
]
FALSE_INT_COMPARISONS: list[tuple[int, str, int]] = [
    *[
        (val, op, val)
        for val in SORTED_INTS
        for op in opposite_ops(
            "=",
            "==",
            "<=",
            ">=",
        )
    ],
    *[
        (left, op, right)
        for left, right in itertools.pairwise(SORTED_INTS)
        for op in opposite_ops(
            "!=",
            "~=",
            "<",
            "<=",
        )
    ],
    *[
        (left, op, right)
        for left, right in zip(
            SORTED_INTS[1:],
            SORTED_INTS,
            strict=False,
        )
        for op in opposite_ops(
            ">",
            ">=",
        )
    ],
]


@pytest.mark.parametrize("comparisons", TRUE_INT_COMPARISONS)
def test_if_true_ints(
    comparisons: tuple[int, str, int],
    tmp_path: Path,
    run_integrated_jobs: Callable[[list[dict[str, Any]]], None],
) -> None:
    """Test taking the if branch."""
    conditional_parms = {
        "left_side": comparisons[0],
        "right_side": comparisons[2],
        "comparator": comparisons[1],
        "if_true": make_if_job(tmp_path),
        "if_false": make_else_job(tmp_path),
    }
    job = {
        "function": "pyantz.jobs.branching.if_else.if_else",
        "parameters": conditional_parms,
    }

    run_integrated_jobs([job])

    assert (tmp_path / "IF.txt").exists()


@pytest.mark.parametrize("comparisons", FALSE_INT_COMPARISONS)
def test_if_false_ints(
    comparisons: tuple[int, str, int],
    tmp_path: Path,
    run_integrated_jobs: Callable[[list[dict[str, Any]]], None],
) -> None:
    """Test taking the if branch."""
    conditional_parms = {
        "left_side": comparisons[0],
        "right_side": comparisons[2],
        "comparator": comparisons[1],
        "if_true": make_if_job(tmp_path),
        "if_false": make_else_job(tmp_path),
    }
    job = {
        "function": "pyantz.jobs.branching.if_else.if_else",
        "parameters": conditional_parms,
    }

    run_integrated_jobs([job])

    assert (tmp_path / "ELSE.txt").exists()
