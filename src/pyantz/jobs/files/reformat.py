"""Reformate between tabular datasets."""

import logging
from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class FromCsvToParquetParameters(BaseModel):
    """Load a csv and dump it into a parquet."""

    model_config = ConfigDict(frozen=True)

    csv_file: Path

    parquet_file: Path


@add_parameters(FromCsvToParquetParameters)
@no_submit_fn
def csv_to_parquet(params: FromCsvToParquetParameters) -> bool:
    """Use polars to load a csv and dump it into a parquet.

    :Example:

    .. testsetup::

        import polars as pl
        pl.DataFrame({
            "a": [1, 2, 3],
            "b": [4.1, 5.1, 6.2],
        }).write_csv("some_csv.csv")

    .. testcode::

        import polars as pl
        from polars.testing import assert_frame_equal

        from pyantz import start

        start({
            "submitter": {
                "type_": "local_proc",
                "working_directory": ".",
            },
            "jobs": [
                {
                    "function": "pyantz.jobs.files.reformat.csv_to_parquet",
                    "parameters": {
                        "csv_file": "some_csv.csv",
                        "parquet_file": "reformatted.parquet",
                    },
                },
            ],
        })

        from_csv = pl.read_csv("some_csv.csv")
        from_parq = pl.read_parquet("reformatted.parquet")

        assert_frame_equal(from_csv, from_parq)

    .. testcleanup::

        import os
        for file in ("some_csv.csv", "reformatted.parquet", "queue.db"):
            if os.path.exists(file):
                os.remove(file)

    """
    logger = logging.getLogger(__name__)

    logger.debug("From %s -> %s", params.csv_file, params.parquet_file)

    if not params.csv_file.exists():
        logger.error("Cannot load csv - doesn't exist: %s", params.csv_file)
        return False

    try:
        pl.scan_csv(
            params.csv_file,
            low_memory=True,
        ).sink_parquet(
            params.parquet_file,
        )
    except Exception as exc:
        logger.exception("Error in CSV->PARQUET", exc_info=exc)
        return False
    else:
        return True


class FromExcelToCsvParameters(BaseModel):
    """Load a page from an excel and dump it into a csv."""

    excel_file: Path

    # name of the sheet in excel to execute
    sheet_name: str | None = None

    csv_file: Path


@add_parameters(FromExcelToCsvParameters)
@no_submit_fn
def excel_to_csv(params: FromExcelToCsvParameters) -> bool:
    """Use polars to load an excel and dump it into a csv.

    :Example:

    .. testsetup::

        import polars as pl
        pl.DataFrame({
            "a": [1, 2, 3],
            "b": [4.1, 5.1, 6.2],
        }).write_excel("some_excel.xlsx")

    .. testcode::

        import polars as pl
        from polars.testing import assert_frame_equal

        from pyantz import start

        start({
            "submitter": {
                "type_": "local_proc",
                "working_directory": ".",
            },
            "jobs": [
                {
                    "function": "pyantz.jobs.files.reformat.excel_to_csv",
                    "parameters": {
                        "excel_file": "some_excel.xlsx",
                        "csv_file": "some_csv.csv",
                    },
                },
            ],
        })

        from_csv = pl.read_excel("some_excel.xlsx")
        from_parq = pl.read_csv("some_csv.csv")

        assert_frame_equal(from_csv, from_parq)

    .. testcleanup::

        import os
        for file in ("some_excel.xlsx", "some_csv.csv", "queue.db"):
            if os.path.exists(file):
                os.remove(file)

    """
    logger = logging.getLogger(__name__)

    logger.debug("From %s -> %s", params.excel_file, params.csv_file)

    if not params.excel_file.exists():
        logger.error("Cannot load excel - doesn't exist: %s", params.excel_file)
        return False

    try:
        pl.read_excel(params.excel_file, sheet_name=params.sheet_name).write_csv(
            params.csv_file
        )
    except Exception as exc:
        logger.exception("Error in CSV->PARQUET", exc_info=exc)
        return False
    else:
        return True
