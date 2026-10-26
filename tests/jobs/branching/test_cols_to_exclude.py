"""Test excluding several columns of the case matrix."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import polars as pl

from pyantz import start
from pyantz.jobs.branching.case_matrix import CaseMatrixExpansionParams

if TYPE_CHECKING:
    from pathlib import Path


def test_several_columns_validate() -> None:
    """A tuple of any length is accepted."""
    for columns in [(), ("a",), ("a", "b"), ("a", "b", "c")]:
        params = CaseMatrixExpansionParams(
            case_matrix_parquet="x",  # ty: ignore[invalid-argument-type]
            cols_to_exclude=columns,
            pipeline_template=[],
        )
        assert params.cols_to_exclude == columns


def test_expansion_excludes_two_columns(tmp_path: Path) -> None:
    """Excluded columns are not variables of the generated pipelines."""
    matrix = tmp_path / "matrix.parquet"
    pl.DataFrame({"a": [1, 2], "b": ["x", "y"], "c": [10, 20]}).write_parquet(matrix)
    out = tmp_path / "out"
    out.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    template: list[dict[str, Any]] = [
        {
            "function": "pyantz.jobs.testing.touch_file.touch_file",
            # c is set for every row; a and b are excluded, so stay unresolved
            "parameters": {"path": os.fspath(out / "c%{c}_a%{a}_b%{b}")},
        },
    ]

    start(
        {
            "jobs": [
                {
                    "function": "pyantz.jobs.branching.case_matrix.pipeline_expansion",
                    "parameters": {
                        "case_matrix_parquet": os.fspath(matrix),
                        "cols_to_exclude": ["a", "b"],
                        "pipeline_template": template,
                    },
                },
            ],
            "submitter": {
                "type_": "local_proc",
                "use_same_proc": True,
                "working_directory": os.fspath(work),
            },
        },
    )

    assert sorted(p.name for p in out.iterdir()) == [
        "c10_a%{a}_b%{b}",
        "c20_a%{a}_b%{b}",
    ]
