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
    """Text file whose words to count."""

    output_file: Path
    """File to write the count to."""


@add_parameters(WordCountParams)
@no_submit_fn
def word_count(params: WordCountParams) -> bool:
    """Count words in a text file and write the count to an output file.

    Args:
        params: the job's parameters, validated as :class:`WordCountParams`.

    Parameters:
        input_file (Path): text file whose words to count.
        output_file (Path): file to write the count to.

    Returns:
        bool: True once the count is written, False if the input doesn't exist.

    Raises:
        OSError: if a file can't be read or written.

    """
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
    """Parquet file to read."""

    destination: Path
    """Parquet file to write the kept rows to."""

    column: str
    """Column to compare with ``min_value``."""

    min_value: float
    """Smallest value of ``column`` which is kept."""


@add_parameters(FilterParquetParams)
@no_submit_fn
def filter_parquet(params: FilterParquetParams) -> bool:
    """Keep only rows where column >= min_value.

    Args:
        params: the job's parameters, validated as :class:`FilterParquetParams`.

    Parameters:
        source (Path): parquet file to read.
        destination (Path): parquet file to write the kept rows to.
        column (str): column to compare with ``min_value``.
        min_value (float): smallest value of ``column`` which is kept.

    Returns:
        bool: True once the rows are written, False if the source doesn't exist.

    Raises:
        polars.exceptions.PolarsError: if the column doesn't exist or the parquet
            can't be read or written.

    """
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
    """One job is submitted per item."""

    output_dir: Path
    """Directory in which each job creates ``<item>.done``."""


@add_parameters(FanOutParams)
def fan_out(params: FanOutParams, submit_fn: SubmissionFnType) -> bool:
    """Dynamically submit one touch-file job per item in the list.

    Args:
        params: the job's parameters, validated as :class:`FanOutParams`.
        submit_fn: function to submit the jobs with.

    Parameters:
        items (list[str]): one job is submitted per item.
        output_dir (Path): directory in which each job creates ``<item>.done``;
            created if missing.

    Returns:
        bool: True once the jobs are submitted.

    Raises:
        OSError: if the output directory can't be created.

    """
    params.output_dir.mkdir(parents=True, exist_ok=True)

    for item in params.items:
        job = JobConfig(
            function="pyantz.jobs.testing.touch_file.touch_file",  # type: ignore[arg-type]
            parameters={"path": str(params.output_dir / f"{item}.done")},
        )
        submit_fn(job)

    return True
