"""Test that all structural problems of a configuration are reported together."""

import os
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config import InitialConfig
from pyantz.infrastructure.config.graph_validation import find_graph_problems
from pyantz.infrastructure.config.job import make_job

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _job(job_id: str, deps: list[str] | None = None) -> dict[str, Any]:
    return {"job_id": job_id, "function": NOP, "parameters": {}, "depends_on": deps}


def _config(jobs: list[dict[str, Any]], tmp_path: Path) -> dict[str, Any]:
    return {
        "jobs": jobs,
        "submitter": {"type_": "local_proc", "working_directory": os.fspath(tmp_path)},
    }


def test_all_problems_in_one_error(tmp_path: Path) -> None:
    """A duplicate, an unknown dependency and a cycle are all listed."""
    jobs = [
        _job("dup"),
        _job("dup"),
        _job("lost", ["ghost"]),
        _job("a", ["b"]),
        _job("b", ["a"]),
    ]

    with pytest.raises(ValidationError) as info:
        InitialConfig.model_validate(_config(jobs, tmp_path))

    message = str(info.value)
    assert "Duplicate job_id 'dup'" in message
    assert "Job 'lost' depends on unknown job 'ghost'" in message
    assert "Dependency cycle" in message
    assert message.count("Invalid jobs") == 1


def test_cycle_names_the_path() -> None:
    """The cycle is shown in order."""
    problems = find_graph_problems(
        [
            make_job(_job("a", ["c"])),
            make_job(_job("b", ["a"])),
            make_job(_job("c", ["b"])),
        ],
    )

    (problem,) = problems
    assert problem.startswith("Dependency cycle: ")
    assert set(problem.removeprefix("Dependency cycle: ").split(" -> ")) == {
        "a",
        "b",
        "c",
    }


def test_valid_graph_has_no_problems(tmp_path: Path) -> None:
    """A good configuration, including dependencies on virtual jobs, is accepted."""
    virtual = {
        "job_id": "v",
        "function": "pyantz.virtual.add_variables.AddVariables",
        "parameters": {"variables": {"a": 1}},
    }
    jobs = [virtual, _job("x", ["v"]), _job("y", ["x"])]

    assert InitialConfig.model_validate(_config(jobs, tmp_path)).jobs
    assert not find_graph_problems(map(make_job, jobs))


def test_unknown_dependency_names_the_job() -> None:
    """Each unknown dependency is reported with the job that has it."""
    problems = find_graph_problems(
        [make_job(_job("j", ["x", "y"]))],
    )

    assert problems == [
        "Job 'j' depends on unknown job 'x'",
        "Job 'j' depends on unknown job 'y'",
    ]


def test_duplicates_were_previously_dropped(tmp_path: Path) -> None:
    """Two jobs with one id are an error instead of silently becoming one job."""
    with pytest.raises(ValidationError, match="Duplicate job_id"):
        InitialConfig.model_validate(_config([_job("x"), _job("x")], tmp_path))
