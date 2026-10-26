"""Test cloning a pipeline template for each row of a case matrix."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import polars as pl

from pyantz import start
from pyantz.infrastructure.config.job import make_job
from pyantz.jobs.branching.case_matrix import _pipeline_factory_factory

if TYPE_CHECKING:
    from pathlib import Path

    from pyantz.infrastructure.config import JobConfig

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _template(*jobs: dict[str, Any]) -> list[JobConfig]:
    return [make_job({"function": NOP, "parameters": {}, **job}) for job in jobs]  # type: ignore[misc]  # ty: ignore[invalid-return-type]


def _clone(template: list[JobConfig]) -> list[JobConfig]:
    submitted: list[JobConfig] = []
    _pipeline_factory_factory(template)({"x": 1})(submitted.append)
    return submitted


def test_parallel_branches_are_kept() -> None:
    """B and C both depend only on A's new id, so they can run in parallel."""
    jobs = _template(
        {"job_id": "A"},
        {"job_id": "B", "depends_on": ["A"]},
        {"job_id": "C", "depends_on": ["A"]},
    )

    a, b, c = _clone(jobs)

    assert b.depends_on == {a.job_id}
    assert c.depends_on == {a.job_id}
    assert not a.depends_on
    assert len({a.job_id, b.job_id, c.job_id}) == 3  # noqa: PLR2004
    assert "A" not in {a.job_id, b.job_id, c.job_id}


def test_external_dependencies_are_kept_and_sets_are_used() -> None:
    """Dependencies outside the template stay, and depends_on is a real set."""
    jobs = _template(
        {"job_id": "A", "depends_on": ["elsewhere"]},
        {"job_id": "B", "depends_on": ["A", "other"]},
    )

    a, b = _clone(jobs)

    assert a.depends_on == {"elsewhere"}
    assert b.depends_on == {a.job_id, "other"}


def test_template_without_structure_runs_in_order() -> None:
    """Without any dependencies in the template, jobs still run in list order."""
    a, b, c = _clone(_template({"job_id": "A"}, {"job_id": "B"}, {"job_id": "C"}))

    assert b.depends_on == {a.job_id}
    assert c.depends_on == {b.job_id}


def test_clones_do_not_share_ids() -> None:
    """Every clone gets its own ids, including for nested jobs."""
    nested = {
        "function": "pyantz.jobs.branching.if_else.if_else",
        "parameters": {
            "left_side": 1,
            "right_side": 1,
            "comparator": "==",
            "if_true": {"job_id": "yes", "function": NOP, "parameters": {}},
            "if_false": {"job_id": "no", "function": NOP, "parameters": {}},
        },
    }
    factory = _pipeline_factory_factory(_template(nested))
    first: list[JobConfig] = []
    second: list[JobConfig] = []
    factory({"x": 1})(first.append)
    factory({"x": 2})(second.append)

    def ids(job: JobConfig) -> set[str]:
        params = job.parameters
        return {job.job_id, params["if_true"]["job_id"], params["if_false"]["job_id"]}

    assert ids(first[0]).isdisjoint(ids(second[0]))
    assert "yes" not in ids(first[0])


def test_nested_dependencies_follow_the_new_ids() -> None:
    """Dependencies between jobs nested in a template job still point at each other."""
    nested = {
        "function": "pyantz.jobs.wrappers.variables.run_jobs_in_context",
        "parameters": {
            "shared_variables": {},
            "jobs": [
                {"job_id": "first", "function": NOP, "parameters": {}},
                {
                    "job_id": "second",
                    "function": NOP,
                    "parameters": {},
                    "depends_on": ["first"],
                },
            ],
        },
    }

    (job,) = _clone(_template(nested))

    first, second = job.parameters["jobs"]
    assert first["job_id"] != "first"
    assert second["depends_on"] == [first["job_id"]]


def test_expansion_with_nested_if_else_runs_every_row(tmp_path: Path) -> None:
    """An if_else template over a 2 row matrix runs both rows."""
    matrix = tmp_path / "matrix.parquet"
    pl.DataFrame({"x": [1, 2]}).write_parquet(matrix)
    out = tmp_path / "out"
    out.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    touch = "pyantz.jobs.testing.touch_file.touch_file"
    template = [
        {
            "function": "pyantz.jobs.branching.if_else.if_else",
            "parameters": {
                "left_side": 1,
                "right_side": 1,
                "comparator": "==",
                "if_true": {
                    "job_id": "yes",
                    "function": touch,
                    "parameters": {"path": os.fspath(out / "IF_%{x}")},
                },
                "if_false": {
                    "job_id": "no",
                    "function": touch,
                    "parameters": {"path": os.fspath(out / "ELSE_%{x}")},
                },
            },
        },
    ]

    start(
        {
            "jobs": [
                {
                    "function": "pyantz.jobs.branching.case_matrix.pipeline_expansion",
                    "parameters": {
                        "case_matrix_parquet": os.fspath(matrix),
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

    assert sorted(p.name for p in out.iterdir()) == ["IF_1", "IF_2"]
