import logging

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config.base import Config, JobConfig
from pyantz.infrastructure.core.job import run_job
from pyantz.infrastructure.core.status import Status

logger = logging.getLogger("test")
logger.setLevel(100000)


def successful_function(*args):
    """Returns success"""
    return Status.SUCCESS


def failed_function(*args):
    """Returns a failure"""
    return Status.ERROR


def error_function(*args):
    """Raises an uncaught exception"""
    raise Exception("Some error")


def fake_submission(c: Config) -> None:
    """Does nothing"""
    pass


def test_getting_functions() -> None:
    """Test that jobs correctly import and link to the function described"""

    job_config: dict = {
        "type": "job",
        "function": "tests.infrastructure.core.test_job.successful_function",
        "parameters": {},
    }
    jc = JobConfig.model_validate(job_config)
    assert jc.function == successful_function
    assert jc.function == successful_function
    assert jc.function(jc.parameters, fake_submission) == Status.SUCCESS

    job_config = {
        "type": "job",
        "function": "tests.infrastructure.core.test_job.failed_function",
        "parameters": {},
    }
    jc = JobConfig.model_validate(job_config)
    assert jc.function == failed_function
    assert jc.function(jc.parameters, fake_submission) == Status.ERROR


def test_running_job_success() -> None:
    """Test that running the success function returns success through the job"""
    job_config: dict = {
        "type": "job",
        "function": "tests.infrastructure.core.test_job.successful_function",
        "parameters": {},
    }
    jc = JobConfig.model_validate(job_config)

    assert run_job(jc, variables={}, logger=logger) == Status.SUCCESS


def test_running_job_failure() -> None:
    """Test that running the failure function returns failure through the job"""
    job_config: dict = {
        "type": "job",
        "function": "tests.infrastructure.core.test_job.failed_function",
        "parameters": {},
    }
    jc = JobConfig.model_validate(job_config)

    assert run_job(jc, variables={}, logger=logger) == Status.ERROR


def test_running_job_exception() -> None:
    """Test that running the exception function returns failure through the job"""
    job_config: dict = {
        "type": "job",
        "function": "tests.infrastructure.core.test_job.error_function",
        "parameters": {},
    }
    jc = JobConfig.model_validate(job_config)

    assert run_job(jc, variables={}, logger=logger) == Status.ERROR


def test_no_function_error() -> None:
    """Test that non existent functions cause a validation error"""
    job_config: dict = {
        "type": "job",
        "function": "tests.infrastructure.core.test_job.NOSUCHFUNCTION",
        "parameters": {},
    }

    with pytest.raises(ValidationError):
        _ = JobConfig.model_validate(job_config)


def test_not_a_callable() -> None:
    """Test that non callable functions cause a validation error"""
    job_config: dict = {
        "type": "job",
        "function": "tests.infrastructure.core.test_job",
        "parameters": {},
    }

    with pytest.raises(ValidationError):
        _ = JobConfig.model_validate(job_config)


def test_not_a_module() -> None:
    """Test that modules not existing for the provided function cause a validation error"""
    job_config: dict = {
        "type": "job",
        "function": "pyantz.no.such.module",
        "parameters": {},
    }
    with pytest.raises(ValidationError):
        _ = JobConfig.model_validate(job_config)
