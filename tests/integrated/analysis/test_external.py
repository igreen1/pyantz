"""Test running external functions."""

import os
from typing import TYPE_CHECKING

import polars as pl
from polars.testing import assert_frame_equal

from pyantz import start

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


def extraction_function(
    cols_names: list[str],
) -> pl.DataFrame:
    """Create a fake dataframe based on user input of the columns."""
    return pl.DataFrame({col: list(range(10)) for col in cols_names})


def simple_external(
    col_names: list[str],
    output_path: Path,
    *,
    success: bool = True,
) -> bool:
    """Save a file for testing."""
    result = extraction_function(
        col_names,
    )

    result.write_parquet(
        output_path,
    )

    return success


def test_external_extract_args(
    tmp_path: Path,
) -> None:
    """Test calling an external extract function."""
    working_dir = tmp_path / "working_dir"
    working_dir.mkdir()
    output_path = tmp_path / "output.parquet"

    config: dict[str, Any] = {
        "jobs": [
            {
                "function": "pyantz.jobs.analysis.external.save_from_external_extraction",
                "parameters": {
                    "function_args": [["a", "b", "c"]],
                    "external_function": "tests.integrated.analysis.test_external.extraction_function",
                    "result_parquet_location": os.fspath(output_path),
                },
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "working_directory": working_dir,
        },
    }

    start(config)

    assert output_path.exists()
    result = pl.read_parquet(output_path)
    expected = pl.DataFrame(
        {
            "a": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "b": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "c": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        }
    )
    assert_frame_equal(expected, result)


def test_external_extract_kwargs(
    tmp_path: Path,
) -> None:
    """Test calling an external extract function."""
    working_dir = tmp_path / "working_dir"
    working_dir.mkdir()
    output_path = tmp_path / "output.parquet"

    config: dict[str, Any] = {
        "jobs": [
            {
                "function": "pyantz.jobs.analysis.external.save_from_external_extraction",
                "parameters": {
                    "function_kwargs": {
                        "cols_names": ["a", "b", "c"],
                    },
                    "external_function": "tests.integrated.analysis.test_external.extraction_function",
                    "result_parquet_location": os.fspath(output_path),
                },
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "working_directory": working_dir,
        },
    }

    start(config)

    assert output_path.exists()
    result = pl.read_parquet(output_path)
    expected = pl.DataFrame(
        {
            "a": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "b": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "c": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        }
    )
    assert_frame_equal(expected, result)


def test_external_simple_args(tmp_path: Path) -> None:
    """Test calling an external function."""
    working_dir = tmp_path / "working_dir"
    working_dir.mkdir()
    output_path = tmp_path / "output.parquet"

    config: dict[str, Any] = {
        "jobs": [
            {
                "function": "pyantz.jobs.analysis.external.external_simple",
                "parameters": {
                    "function_args": [["a", "b", "c", "d"], os.fspath(output_path)],
                    "external_function": "tests.integrated.analysis.test_external.simple_external",
                },
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "working_directory": working_dir,
        },
    }

    start(config)

    assert output_path.exists()
    result = pl.read_parquet(output_path)
    expected = pl.DataFrame(
        {
            "a": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "b": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "c": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "d": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        }
    )
    assert_frame_equal(expected, result)


def test_external_simple_kwargs(tmp_path: Path) -> None:
    """Test calling an external function."""
    working_dir = tmp_path / "working_dir"
    working_dir.mkdir()
    output_path = tmp_path / "output.parquet"

    config: dict[str, Any] = {
        "jobs": [
            {
                "function": "pyantz.jobs.analysis.external.external_simple",
                "parameters": {
                    "function_args": [
                        ["a", "b", "c", "d"],
                    ],
                    "function_kwargs": {
                        "output_path": os.fspath(output_path),
                    },
                    "external_function": "tests.integrated.analysis.test_external.simple_external",
                },
            },
        ],
        "submitter": {
            "type_": "local_proc",
            "working_directory": working_dir,
        },
    }

    start(config)

    assert output_path.exists()
    result = pl.read_parquet(output_path)
    expected = pl.DataFrame(
        {
            "a": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "b": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "c": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "d": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        }
    )
    assert_frame_equal(expected, result)
