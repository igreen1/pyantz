"""Test that job-typed parameters containing non-jobs don't crash compilation."""

from typing import Any

import pytest

from pyantz.infrastructure.config import JobConfig
from pyantz.infrastructure.config.fn_utils import import_function_by_name
from pyantz.infrastructure.virtual import compile_virtual

NOP = "pyantz.jobs.testing.nop.do_nothing"
RUN_IN_CONTEXT = "pyantz.jobs.wrappers.variables.run_jobs_in_context"


def _job_with_pipeline(sub_jobs: list[Any]) -> JobConfig:
    """Build the job without start-up validation, as when it is disabled."""
    return JobConfig.model_construct(
        job_id="outer",
        function=import_function_by_name(RUN_IN_CONTEXT),
        parameters={"shared_variables": {}, "jobs": sub_jobs},
        depends_on=None,
        strict=False,
        name=None,
        num_attempted_runs=0,
        virtual=False,
    )


@pytest.mark.parametrize(
    "bad_item",
    [
        {"not": "a job"},
        {"function": NOP, "parameters": "not a mapping"},
        "just a string",
    ],
)
def test_non_job_in_pipeline_is_left_untouched(bad_item: Any) -> None:  # noqa: ANN401
    """A pipeline parameter with a non-job entry is not compiled, and not a crash."""
    sub_jobs = [{"function": NOP, "parameters": {}}, bad_item]

    (compiled,) = compile_virtual([_job_with_pipeline(sub_jobs)])

    assert compiled.parameters["jobs"] == sub_jobs


def test_valid_pipeline_entries_are_validated() -> None:
    """Pipelines consisting only of jobs are still turned into job configs."""
    sub_jobs = [{"function": NOP, "parameters": {}}]

    (compiled,) = compile_virtual([_job_with_pipeline(sub_jobs)])

    (sub_job,) = compiled.parameters["jobs"]
    assert isinstance(sub_job, JobConfig)
