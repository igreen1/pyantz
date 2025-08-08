"""Test writing a parquet from a csv."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import polars as pl
from polars.testing import assert_frame_equal

from pyantz.jobs.analysis.csv_to_parquet import csv_to_parquet

if TYPE_CHECKING:
    import pytest


def test_csv_to_parquet_simple(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Test making a simple parquet from a csv."""
    tmpdir = tmp_path_factory.mktemp("test_csv")
    csv_file = tmpdir / "input.csv"
    parquet_file = tmpdir / "output.parquet"
    job_params = {
        "input_file": str(csv_file),
        "output_file": str(parquet_file),
    }

    test_data = pl.DataFrame({"a": [1, 2, 3], "b": ["a", "b", "c"]})
    test_data.write_csv(csv_file)

    csv_to_parquet(job_params, logging.getLogger("TESTING"))
    assert_frame_equal(test_data, pl.read_parquet(parquet_file))
