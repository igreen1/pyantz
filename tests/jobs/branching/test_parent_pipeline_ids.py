"""Test nested pipeline expansions know the ids of their parent pipelines."""

import os
from typing import TYPE_CHECKING, Any

import polars as pl

from pyantz import start

if TYPE_CHECKING:
    from pathlib import Path

EXPAND = "pyantz.jobs.branching.case_matrix.pipeline_expansion_with_output_dir"


def _matrix(path: Path, rows: int, column: str = "x") -> str:
    pl.DataFrame({column: list(range(rows))}).write_parquet(path)
    return os.fspath(path)


def _run(tmp_path: Path, outer: dict[str, Any]) -> None:
    work = tmp_path / "work"
    work.mkdir()
    start(
        {
            "jobs": [{"function": EXPAND, "parameters": outer}],
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": True,
                "working_directory": os.fspath(work),
            },
        },
    )


def test_inner_jobs_see_the_outer_pipeline_id(tmp_path: Path) -> None:
    """Inner jobs get parent_pipeline_id equal to the outer pipeline's id."""
    out = tmp_path / "out"
    marks = tmp_path / "marks"
    marks.mkdir()
    inner_template = [
        {
            "function": "pyantz.jobs.testing.touch_file.touch_file",
            "parameters": {"path": os.fspath(marks / "p%{parent_pipeline_id}_y%{y}")},
        },
    ]
    outer_template = [
        {
            "function": EXPAND,
            "parameters": {
                "case_matrix_parquet": _matrix(tmp_path / "inner.parquet", 2, "y"),
                "output_dir": "%{output_dir}/inner",
                "pipeline_template": inner_template,
            },
        },
    ]

    _run(
        tmp_path,
        {
            "case_matrix_parquet": _matrix(tmp_path / "outer.parquet", 2),
            "output_dir": os.fspath(out),
            "pipeline_template": outer_template,
        },
    )

    # inner variables are not resolved early by the outer job, as they only exist
    # for the inner rows; the parent id comes from the outer pipeline
    assert sorted(p.name for p in marks.iterdir()) == [
        "p0_y0",
        "p0_y1",
        "p1_y0",
        "p1_y1",
    ]


def test_nested_output_directories_are_created(tmp_path: Path) -> None:
    """Missing parents of the output directory are created."""
    out = tmp_path / "a" / "b" / "out"

    _run(
        tmp_path,
        {
            "case_matrix_parquet": _matrix(tmp_path / "m.parquet", 2),
            "output_dir": os.fspath(out),
            "pipeline_template": [
                {
                    "function": "pyantz.jobs.testing.nop.do_nothing",
                    "parameters": {},
                },
            ],
        },
    )

    assert (out / "run_0").is_dir()
    assert (out / "run_1").is_dir()
