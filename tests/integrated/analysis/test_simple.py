"""Test simple jobs."""

import os
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Final

import polars as pl
from polars.testing import assert_frame_equal

from pyantz import start

if TYPE_CHECKING:
    from pathlib import Path

JOIN_CONFIG: Final[dict[str, Any]] = {
    "jobs": [
        {
            "function": "pyantz.jobs.analysis.simple.join_parquets",
            "parameters": {},
        }
    ],
    "submitter": {
        "type_": "local_proc",
        # "working_directory" # set in test
    },
}


def test_join_parquets(tmp_path: Path) -> None:
    """Create a configuration for joining parquets."""
    config = deepcopy(JOIN_CONFIG)

    working_dir = tmp_path / "working_dir"
    working_dir.mkdir(exist_ok=True)
    config["submitter"]["working_directory"] = os.fspath(working_dir)

    left_df = pl.DataFrame(
        {
            "idx": [1, 2, 3, 4, 5],
            "a": [10, 11, 12, 13, 14],
        }
    )
    left_path = tmp_path / "left.parquet"
    left_df.write_parquet(left_path)

    right_df = pl.DataFrame(
        {
            "idx": [1, 4],
            "b": ["hello", "world"],
        }
    )
    right_path = tmp_path / "right.parquet"
    right_df.write_parquet(right_path)

    output_path = tmp_path / "output.parquet"

    config["jobs"][0]["parameters"] = {
        "left_parquet": left_path,
        "right_parquet": right_path,
        "how": "inner",
        "output_parquet": output_path,
        "on_": "idx",
    }

    start(config)

    assert output_path.exists()

    expected = left_df.join(right_df, on="idx", how="inner")
    result = pl.read_parquet(output_path)

    assert_frame_equal(expected, result)
