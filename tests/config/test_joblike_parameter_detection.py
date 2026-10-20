"""Test finding job-typed parameters of a job function."""

import os
from typing import Any

from pydantic import BaseModel

from pyantz.infrastructure.config import (
    JobConfig,
    JobPipeline,
    VirtualJobConfig,
    add_parameters,
    no_submit_fn,
)
from pyantz.infrastructure.config.fn_utils import import_function_by_name
from pyantz.infrastructure.virtual import compile_virtual
from pyantz.infrastructure.virtual.compile import _find_joblike_parameters_with_model

NOP = "pyantz.jobs.testing.nop.do_nothing"


class _ManyJobFields(BaseModel):
    a: JobConfig
    b: list[JobConfig]
    c: tuple[JobConfig, ...]
    d: JobConfig | None
    e: JobPipeline
    f: list[str]
    g: str
    h: dict[str, JobConfig | VirtualJobConfig]


@add_parameters(_ManyJobFields)
@no_submit_fn
def _job_fn(_params: _ManyJobFields) -> bool:
    return True


def _model_construct(
    function: Any,  # noqa: ANN401
    parameters: dict[str, Any],
) -> JobConfig:
    """Build a job without start-up validation."""
    return JobConfig.model_construct(
        job_id="outer",
        function=function,
        parameters=parameters,
        depends_on=None,
        strict=False,
        name=None,
        num_attempted_runs=0,
        virtual=False,
    )


def test_detects_single_and_iterable_job_fields() -> None:
    """Nested, optional, tuple and aliased annotations are all understood."""
    job = _model_construct(_job_fn, {})

    result = _find_joblike_parameters_with_model(job)

    assert result is not None
    single, iterable = result
    assert set(single) == {"a", "d"}
    assert set(iterable) == {"b", "c", "e"}


def test_virtual_job_nested_in_submit_is_compiled() -> None:
    """A virtual AddVariables job inside `submit`'s tuple of jobs is compiled."""
    submit = import_function_by_name("pyantz.jobs.wrappers.submit.submit")
    parameters = {
        "runner_config": {"type_": "local_proc", "working_directory": os.fspath("/x")},
        "jobs": [
            {
                "job_id": "v",
                "function": "pyantz.virtual.add_variables.AddVariables",
                "parameters": {"variables": {"a": 1}},
            },
            {
                "job_id": "real",
                "function": NOP,
                "parameters": {},
                "depends_on": ["v"],
            },
        ],
    }

    (compiled,) = compile_virtual([_model_construct(submit, parameters)])

    nested = compiled.parameters["jobs"]
    assert nested
    assert all(isinstance(j, JobConfig) and not j.virtual for j in nested)
    assert "v" not in {dep for j in nested for dep in (j.depends_on or set())}
