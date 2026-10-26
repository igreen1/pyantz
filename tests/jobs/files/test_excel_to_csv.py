"""Test converting excel files to csv."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import polars as pl
import pytest

from pyantz.jobs.files.reformat import FromExcelToCsvParameters, excel_to_csv

if TYPE_CHECKING:
    from pathlib import Path


def _convert(excel: Path, csv: Path) -> bool:
    params = FromExcelToCsvParameters(excel_file=excel, csv_file=csv)
    return excel_to_csv(params.model_dump(), lambda *_: None)


def test_missing_fastexcel_gives_a_helpful_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Without fastexcel the job fails and says how to install it."""
    excel = tmp_path / "book.xlsx"
    excel.write_bytes(b"not really excel")

    def _no_fastexcel(*_args: object, **_kwargs: object) -> pl.DataFrame:
        msg = "No module named 'fastexcel'"
        raise ModuleNotFoundError(msg)

    monkeypatch.setattr(pl, "read_excel", _no_fastexcel)

    with caplog.at_level(logging.ERROR):
        assert _convert(excel, tmp_path / "out.csv") is False

    assert "pip install pyantz[excel]" in caplog.text


def test_other_errors_are_labelled_correctly(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A broken workbook fails with an Excel->CSV message (not CSV->PARQUET)."""
    excel = tmp_path / "broken.xlsx"
    excel.write_bytes(b"not really excel")

    with caplog.at_level(logging.ERROR):
        assert _convert(excel, tmp_path / "out.csv") is False

    assert "Excel->CSV" in caplog.text
    assert "CSV->PARQUET" not in caplog.text


def test_excel_is_converted(tmp_path: Path) -> None:
    """A real workbook is written out as csv."""
    pytest.importorskip("fastexcel")
    excel = tmp_path / "book.xlsx"
    pl.DataFrame({"a": [1, 2], "b": [3.5, 4.5]}).write_excel(excel)
    csv = tmp_path / "out.csv"

    assert _convert(excel, csv) is True

    assert pl.read_csv(csv).to_dict(as_series=False) == {"a": [1, 2], "b": [3.5, 4.5]}


def test_excel_extra_is_declared() -> None:
    """The package declares the optional dependency."""
    from importlib.metadata import metadata  # noqa: PLC0415

    extras = metadata("pyantz").get_all("Provides-Extra") or []
    assert "excel" in extras
