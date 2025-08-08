""" "Test infrastructre calls, leading to 100% test completion."""

import pytest
from pydantic import BaseModel, ValidationError

from pyantz.infrastructure.config.base import (
    JobConfig,
    MutableJobConfig,
    SubmitterJobConfig,
)
from pyantz.infrastructure.config.get_functions import (
    get_function_by_name_strongly_typed,
    get_job_type,
)
from pyantz.infrastructure.core.status import Status


def nop_job() -> None:
    """A job that does nothing."""
    return Status.SUCCESS


def nop_job_with_bad_parameters() -> None:
    """A job that does nothing."""
    return Status.SUCCESS


nop_job_with_bad_parameters.__pyantz_param_model__ = "AGH"


def test_no_job_type() -> None:
    """Test that a job import with no type raises a validation error."""
    func_name = "tests.jobs.test_job_infrastructure.nop_job"

    assert get_job_type(func_name) is None

    assert get_function_by_name_strongly_typed("job", strict=True)(func_name) is None


def test_no_job_function_name() -> None:
    job_config = {"type": "job", "name": "nop_job", "function": 1, "parameters": {}}

    with pytest.raises(ValidationError):
        JobConfig.model_validate(job_config)


def test_serialize_simple_job_config() -> None:
    """Test serialize job config."""
    job_config = {
        "type": "job",
        "function": "tests.jobs.test_job_infrastructure.nop_job",
        "name": "nop_job",
        "parameters": {},
    }

    job = JobConfig.model_validate(job_config)
    dumped = job.model_dump()
    dumped = {k: v for k, v in dumped.items() if k != "id"}
    assert dumped == job_config


def test_serialize_mutable_job_config() -> None:
    """Test serialize job config."""
    job_config = {
        "type": "mutable_job",
        "function": "tests.jobs.test_job_infrastructure.nop_job",
        "name": "nop_job",
        "parameters": {},
    }

    job = MutableJobConfig.model_validate(job_config)
    dumped = job.model_dump()
    dumped = {k: v for k, v in dumped.items() if k != "id"}
    assert dumped == job_config


def test_serialize_submitter_job_config() -> None:
    """Test serialize job config."""
    job_config = {
        "type": "submitter_job",
        "function": "tests.jobs.test_job_infrastructure.nop_job",
        "name": "nop_job",
        "parameters": {},
    }

    job = SubmitterJobConfig.model_validate(job_config)
    dumped = job.model_dump()
    dumped = {k: v for k, v in dumped.items() if k != "id"}
    assert dumped == job_config


def test_job_config_rejects_wrong_type() -> None:
    """Tests that the job config rejects a wrong type."""
    job_config = {
        "type": "mutable_job",
        "function": "tests.jobs.test_job_infrastructure.nop_job",
        "name": "nop_job",
        "parameters": {},
    }

    with pytest.raises(ValidationError):
        JobConfig.model_validate(job_config)


def test_bad_parameters_type_is_rejected() -> None:
    job_config = {
        "type": "job",
        "function": "tests.jobs.test_job_infrastructure.nop_job_with_bad_parameters",
        "name": "nop_job",
        "parameters": {},
    }

    # allowed because this is not in the `pyantz` library
    JobConfig.model_validate(job_config)
