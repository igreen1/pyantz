"""Test the file format conversion jobs."""

from typing import TYPE_CHECKING

import polars as pl

from pyantz.jobs.files.reformat import (
    FromCsvToParquetParameters,
    FromExcelToCsvParameters,
    csv_to_parquet,
    excel_to_csv,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_csv_to_parquet(tmp_path: Path) -> None:
    """The csv is converted, keeping its contents."""
    csv = tmp_path / "in.csv"
    pl.DataFrame({"a": [1, 2], "b": ["x", "y"]}).write_csv(csv)
    params = FromCsvToParquetParameters(
        csv_file=csv, parquet_file=tmp_path / "out.parquet"
    )

    assert csv_to_parquet(params.model_dump(), lambda *_: None) is True

    assert pl.read_parquet(params.parquet_file).to_dicts() == [
        {"a": 1, "b": "x"},
        {"a": 2, "b": "y"},
    ]


def test_csv_to_parquet_missing_file(tmp_path: Path) -> None:
    """A csv which doesn't exist fails the job."""
    params = FromCsvToParquetParameters(
        csv_file=tmp_path / "missing.csv", parquet_file=tmp_path / "out.parquet"
    )

    assert csv_to_parquet(params.model_dump(), lambda *_: None) is False


def test_csv_to_parquet_unwritable_destination(tmp_path: Path) -> None:
    """A destination which can't be written fails the job."""
    csv = tmp_path / "in.csv"
    csv.write_text("a\n1\n")
    params = FromCsvToParquetParameters(
        csv_file=csv, parquet_file=tmp_path / "no" / "out.parquet"
    )

    assert csv_to_parquet(params.model_dump(), lambda *_: None) is False


def test_excel_to_csv_missing_file(tmp_path: Path) -> None:
    """An excel file which doesn't exist fails the job."""
    params = FromExcelToCsvParameters(
        excel_file=tmp_path / "missing.xlsx", csv_file=tmp_path / "out.csv"
    )

    assert excel_to_csv(params.model_dump(), lambda *_: None) is False


def test_excel_to_csv_unreadable_file(tmp_path: Path) -> None:
    """A file which isn't excel fails the job."""
    excel = tmp_path / "bad.xlsx"
    excel.write_text("not excel")
    params = FromExcelToCsvParameters(excel_file=excel, csv_file=tmp_path / "out.csv")

    assert excel_to_csv(params.model_dump(), lambda *_: None) is False
