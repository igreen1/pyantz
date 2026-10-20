"""Test the logging of the columnar operation job."""

import logging
from typing import TYPE_CHECKING

import polars as pl

from pyantz.jobs.analysis.simple import (
    ColumnarOperationParameters,
    columnar_operation,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _run(source: Path, result: Path) -> bool:
    params = ColumnarOperationParameters(
        source_parquet_file=source,
        result_parquet_file=str(result),
        left_col="a",
        right_col="b",
        result_col="c",
        operation="+",
    )
    return columnar_operation(params.model_dump(), lambda *_: None)


def test_missing_source_logs_an_error_without_a_fake_traceback(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The log has the message but no `NoneType: None` traceback."""
    with caplog.at_level(logging.ERROR):
        assert _run(tmp_path / "missing.parquet", tmp_path / "out.parquet") is False

    assert "no such file" in caplog.text
    assert "missing.parquet" in caplog.text
    assert "NoneType: None" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_operation_still_works(tmp_path: Path) -> None:
    """The happy path is unchanged."""
    source = tmp_path / "in.parquet"
    pl.DataFrame({"a": [1, 2], "b": [10, 20]}).write_parquet(source)
    result = tmp_path / "out.parquet"

    assert _run(source, result) is True

    assert pl.read_parquet(result)["c"].to_list() == [11, 22]
