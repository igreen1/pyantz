"""Test the value ranges which make up a case matrix."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import polars as pl
import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.runner.job_manager import run_job
from pyantz.jobs.branching.case_matrix import (
    CaseMatrixCreator,
    ContinuousRange,
    DiscreteRange,
)

if TYPE_CHECKING:
    from pathlib import Path

CREATE = "pyantz.jobs.branching.case_matrix.create_case_matrix"


@pytest.mark.parametrize("step", [0, -1, -0.5])
def test_non_positive_step_is_rejected(step: float) -> None:
    """A step which can't make progress is an error, not an infinite loop."""
    with pytest.raises(ValidationError, match="step must be greater than 0"):
        ContinuousRange(min_value=0, max_value=10, step=step)


def test_float_range_has_no_accumulated_error() -> None:
    """0..0.3 in steps of 0.1 gives three clean values."""
    values = list(ContinuousRange(min_value=0.0, max_value=0.3, step=0.1).get_values())

    assert values == [0.0, 0.1, 0.2]


def test_float_range_excludes_the_maximum() -> None:
    """The maximum is not included, even when float division is noisy."""
    values = list(ContinuousRange(min_value=0.3, max_value=0.9, step=0.2).get_values())

    assert values == [0.3, 0.5, 0.7]


def test_int_range_and_empty_range() -> None:
    """Integers stay integers, and a range with min >= max is empty."""
    assert list(ContinuousRange(min_value=1, max_value=10, step=3).get_values()) == [
        1,
        4,
        7,
    ]
    assert not list(ContinuousRange(min_value=5, max_value=5, step=1).get_values())
    assert not list(ContinuousRange(min_value=5, max_value=1, step=1).get_values())


def test_discrete_range_keeps_order_and_drops_repeats() -> None:
    """Values are used in the order given, once each."""
    values = DiscreteRange[Any](possible_values=["c", "a", "b", "a", "c"])

    assert list(values.get_values()) == ["c", "a", "b"]


def test_discrete_range_accepts_unhashable_values() -> None:
    """Lists and dicts are allowed as values."""
    values = DiscreteRange[Any](possible_values=[[1, 2], {"a": 1}, [1, 2]])

    assert list(values.get_values()) == [[1, 2], {"a": 1}]


def test_empty_variables_are_rejected() -> None:
    """A case matrix needs at least one variable."""
    with pytest.raises(ValidationError):
        CaseMatrixCreator(variables={}, save_file="x.parquet")


def test_created_matrix_is_the_ordered_product(tmp_path: Path) -> None:
    """The saved matrix has the product in a stable order."""
    save_file = tmp_path / "matrix.parquet"
    parameters: dict[str, Any] = {
        "save_file": os.fspath(save_file),
        "variables": {
            "x": {"range": {"possible_values": [3, 1, 2]}},
            "y": {"range": {"min_value": 0.0, "max_value": 0.3, "step": 0.1}},
        },
    }

    job = JobWithContext.model_validate({"function": CREATE, "parameters": parameters})
    assert run_job(job, lambda *_: None) is True

    matrix = pl.read_parquet(save_file)
    assert matrix["x"].to_list() == [3, 3, 3, 1, 1, 1, 2, 2, 2]
    assert matrix["y"].to_list() == [0.0, 0.1, 0.2] * 3
