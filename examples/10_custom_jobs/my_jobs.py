"""Example custom job functions for use in pyantz pipelines.

To use these in a pipeline JSON, reference them as:
    "pyantz_examples.examples.10_custom_jobs.my_jobs.word_count"
or, more practically, install this in your project and use your package name.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
from pydantic import BaseModel

from pyantz.infrastructure.config import add_parameters, no_submit_fn
from pyantz.infrastructure.config.job import JobConfig, SubmissionFnType


class WordCountParams(BaseModel):
    """Count words in a text file and save the result."""

    input_file: Path
    output_file: Path


@add_parameters(WordCountParams)
@no_submit_fn
def word_count(params: WordCountParams) -> bool:
    """Count words in a text file and write the count to an output file."""
    logger = logging.getLogger(__name__)

    if not params.input_file.exists():
        logger.error("Input file not found: %s", params.input_file)
        return False

    text = params.input_file.read_text(encoding="utf-8")
    count = len(text.split())
    params.output_file.write_text(str(count), encoding="utf-8")
    logger.info("Word count: %d -> %s", count, params.output_file)
    return True


class FilterParquetParams(BaseModel):
    """Filter rows in a Parquet file by a column threshold."""

    source: Path
    destination: Path
    column: str
    min_value: float


@add_parameters(FilterParquetParams)
@no_submit_fn
def filter_parquet(params: FilterParquetParams) -> bool:
    """Keep only rows where column >= min_value."""
    logger = logging.getLogger(__name__)

    if not params.source.exists():
        logger.error("Source parquet not found: %s", params.source)
        return False

    (
        pl.scan_parquet(params.source)
        .filter(pl.col(params.column) >= params.min_value)
        .sink_parquet(params.destination)
    )
    return True


class FanOutParams(BaseModel):
    """Submit one job per item in a list — dynamic fan-out."""

    items: list[str]
    output_dir: Path


@add_parameters(FanOutParams)
def fan_out(params: FanOutParams, submit_fn: SubmissionFnType) -> bool:
    """Dynamically submit one touch-file job per item in the list."""
    params.output_dir.mkdir(parents=True, exist_ok=True)

    for item in params.items:
        job = JobConfig(
            function="pyantz.jobs.testing.touch_file.touch_file",  # type: ignore[arg-type]
            parameters={"path": str(params.output_dir / f"{item}.done")},
        )
        submit_fn(job)

    return True
