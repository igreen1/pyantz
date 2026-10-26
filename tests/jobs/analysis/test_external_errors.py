"""Test failure handling of the external analysis jobs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import polars as pl

from pyantz.jobs.analysis.external import (
    ExternalAnalysisParams,
    ExternalExtractParams,
    external_analysis,
    save_from_external_extraction,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

NOP = "pyantz.jobs.testing.nop.do_nothing"


def make_frame() -> pl.DataFrame:
    """Build the frame saved by the extraction tests."""
    return pl.DataFrame({"a": [1, 2, 3]})


def test_missing_parquet_returns_false_with_a_log(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A parquet file which doesn't exist fails the job instead of raising."""
    params = ExternalAnalysisParams(
        variable_names_to_parquets={"data": tmp_path / "missing.parquet"},
        lazy_or_eager="eager",
        external_function=NOP,  # ty: ignore[invalid-argument-type]
    )

    with caplog.at_level(logging.ERROR):
        assert external_analysis(params.model_dump(), lambda *_: None) is False

    assert "Cannot load the data" in caplog.text


def test_unreadable_parquet_returns_false(tmp_path: Path) -> None:
    """A file which isn't parquet fails the job when read eagerly."""
    broken = tmp_path / "broken.parquet"
    broken.write_text("not parquet")
    params = ExternalAnalysisParams(
        variable_names_to_parquets={"data": broken},
        lazy_or_eager="eager",
        external_function=NOP,  # ty: ignore[invalid-argument-type]
    )

    assert external_analysis(params.model_dump(), lambda *_: None) is False


def test_extraction_creates_missing_directories(tmp_path: Path) -> None:
    """The result's directory is created if it doesn't exist."""
    target = tmp_path / "a" / "b" / "result.parquet"
    params = ExternalExtractParams(
        external_function=f"{__name__}.make_frame",  # ty: ignore[invalid-argument-type]
        result_parquet_location=str(target),
    )

    assert save_from_external_extraction(params.model_dump(), lambda *_: None) is True

    assert pl.read_parquet(target)["a"].to_list() == [1, 2, 3]


def test_unregistered_variable_still_fails_cleanly(tmp_path: Path) -> None:
    """A variable with no lazy/eager choice fails the job."""
    data = tmp_path / "d.parquet"
    make_frame().write_parquet(data)
    params = ExternalAnalysisParams(
        variable_names_to_parquets={"data": data},
        lazy_or_eager={"other": "lazy"},  # ty: ignore[invalid-argument-type]
        external_function=NOP,  # ty: ignore[invalid-argument-type]
    )

    assert external_analysis(params.model_dump(), lambda *_: None) is False
