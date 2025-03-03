"""Test filtering a parquet file"""

import logging
import os
from pathlib import Path

import pandas as pd
import pandas.testing

from pyantz.infrastructure.config.base import JobConfig
from pyantz.infrastructure.core.job import run_job
from pyantz.infrastructure.core.status import Status


def test_filter_parquet_job(tmpdir: Path) -> None:
    """Test a simple filter"""

    input_file = os.path.join(tmpdir, "input_file.parq")
    output_file = os.path.join(tmpdir, "output_file.parquet")
    original = pd.DataFrame(
        {
            "a": [i for i in range(100)],
            "b": [i + 0.01 for i in range(100)],
            "c": ["a" for _ in range(100)],
        }
    )
    original.to_parquet(input_file, engine="pyarrow")
    original = original.convert_dtypes(dtype_backend="pyarrow")

    config = {
        "type": "job",
        "function": "pyantz.jobs.analysis.filter_parquet.filter_parquet",
        "parameters": {
            "input_file": input_file,
            "output_file": output_file,
            "left": "a",
            "op": ">",
            "right": 50,
        },
    }

    j1 = JobConfig.model_validate(config)

    assert run_job(j1, {}, logging.getLogger("test")) == Status.SUCCESS

    assert os.path.exists(output_file)
    result = pd.read_parquet(output_file, engine="pyarrow", dtype_backend="pyarrow")

    expected = original.loc[original["a"] > 50]

    pandas.testing.assert_frame_equal(
        expected.reset_index(drop=True), result.reset_index(drop=True)
    )
