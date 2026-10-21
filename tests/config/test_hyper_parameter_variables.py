"""Test variables are resolved in a job's id, name and dependencies."""

from __future__ import annotations

from pyantz.infrastructure.config import JobConfig, JobWithContext

NOP = "pyantz.jobs.testing.nop.do_nothing"


def test_id_name_and_dependencies_are_resolved() -> None:
    """job_id, name and depends_on are filled in from the variables."""
    job = JobWithContext(
        job_id="j_%{i}",
        name="n_%{i}",
        depends_on={"d_%{i}"},
        variables={"i": 1},
        function=NOP,  # ty: ignore[invalid-argument-type]
        parameters={},
    )

    assert job.job_id == "j_1"
    assert job.name == "n_1"
    assert job.depends_on == {"d_1"}
    assert isinstance(job.depends_on, set)


def test_resolution_survives_a_round_trip() -> None:
    """A resolved job serializes and loads back unchanged."""
    job = JobWithContext(
        job_id="j_%{i}",
        depends_on={"d_%{i}", "other"},
        variables={"i": "x"},
        function=NOP,  # ty: ignore[invalid-argument-type]
        parameters={},
    )

    assert JobWithContext.model_validate_json(job.model_dump_json()) == job
    assert job.depends_on == {"d_x", "other"}


def test_unset_variables_are_left_in_place() -> None:
    """References to variables which aren't set remain for later resolution."""
    job = JobWithContext(
        job_id="j_%{missing}",
        name="plain",
        variables={"i": 1},
        function=NOP,  # ty: ignore[invalid-argument-type]
        parameters={},
    )
    assert job.job_id == "j_%{missing}"
    assert job.name == "plain"


def test_resolved_dependencies_from_list_are_coerced_to_set() -> None:
    """Raw (JSON-like) lists are resolved and then validated into a set."""
    job = JobWithContext.model_validate(
        {
            "job_id": "j",
            "depends_on": ["d_%{i}", "d_%{i}"],
            "variables": {"i": 2},
            "function": NOP,
            "parameters": {},
        },
    )
    assert job.depends_on == {"d_2"}


def test_plain_job_config_unaffected() -> None:
    """Jobs without context keep their templates untouched."""
    job = JobConfig(
        job_id="j_%{i}",
        function=NOP,  # ty: ignore[invalid-argument-type]
        parameters={},
    )
    assert job.job_id == "j_%{i}"
