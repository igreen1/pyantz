"""Test that job configs can be made and checked."""

import json
import uuid

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config.base import JobConfig
from pyantz.infrastructure.core.status import Status


def fake_function(*_args) -> Status:
    """A simple fake function for testing."""
    return Status.ERROR


def test_job_import() -> None:
    """Test that the configuration imports the function."""
    job_config = {
        "type": "job",
        "name": "my job",
        "function": "tests.infrastructure.config.test_job_configs.fake_function",
        "parameters": {"s": 1},
    }

    j1 = JobConfig.model_validate(job_config)
    assert j1.function == fake_function


def test_failed_to_find_job() -> None:
    """Test that a validation error is thrown when the function isn't found."""
    job_config = {
        "type": "job",
        "name": "my job",
        "function": "tests.infrastructure.config.test_job_configs.AGHS",
        "parameters": {"s": 1},
    }

    with pytest.raises(ValidationError):
        _ = JobConfig.model_validate(job_config)


def test_not_a_callable() -> None:
    """Test that a validation report is thrown when the function is not a callable."""
    job_config = {
        "type": "job",
        "name": "my job",
        "function": "tests.infrastructure.config.test_job_configs",
        "parameters": {"s": 1},
    }

    with pytest.raises(ValidationError):
        _ = JobConfig.model_validate(job_config)


def test_no_such_module() -> None:
    """Test that a validation error is thrown when the module of the function doesn't exist."""
    job_config = {
        "type": "job",
        "name": "my job",
        "function": "tests.infrastructure.configxxxx.test_job_configs",
        "parameters": {"s": 1},
    }

    with pytest.raises(ValidationError):
        _ = JobConfig.model_validate(job_config)


def test_job_uuid_creation() -> None:
    """Test that all jobs are given UUIDs."""
    job_config = {
        "type": "job",
        "name": "my job",
        "function": "tests.infrastructure.config.test_job_configs.fake_function",
        "parameters": {"s": 1},
    }

    j1 = JobConfig.model_validate(job_config)
    j2 = JobConfig.model_validate(job_config)
    assert j1.id != j2.id

    job_config_str: str = json.dumps(job_config)
    j1 = JobConfig.model_validate_json(job_config_str)
    j2 = JobConfig.model_validate_json(job_config_str)
    assert j1.id != j2.id


def test_job_uuid_override() -> None:
    """Test that a configuration can override the UUID."""
    job_config = {
        "type": "job",
        "id": "cb13bc78-e4a2-4a69-8a54-04ef168d656e",
        "name": "my job",
        "function": "tests.infrastructure.config.test_job_configs.fake_function",
        "parameters": {"s": 1},
    }

    j1 = JobConfig.model_validate(job_config)
    j2 = JobConfig.model_validate(job_config)
    assert j1.id == j2.id  # should be the same because we overrode
    assert j1.id == uuid.UUID("cb13bc78-e4a2-4a69-8a54-04ef168d656e")


def test_empty_job_parameters() -> None:
    """Test that a validation error is thrown if a parameter is not provided
    (Empty dict is allowed but not None to increase explicit-ness).
    """
    job_config = {
        "type": "job",
        "name": "my job",
        "function": "tests.infrastructure.config.test_job_configs.fake_function",
        "parameters": {},
    }
    _j1 = JobConfig.model_validate(job_config)

    with pytest.raises(ValidationError):
        job_config = {
            "type": "job",
            "name": "my job",
            "function": "tests.infrastructure.config.test_job_configs.fake_function",
        }
        _j1 = JobConfig.model_validate(job_config)


def test_job_frozen_attr() -> None:
    """Test that attributes can't be edited on frozen classes."""
    job_config = {
        "type": "job",
        "name": "my job",
        "function": "tests.infrastructure.config.test_job_configs.fake_function",
        "parameters": {},
    }
    j1 = JobConfig.model_validate(job_config)

    with pytest.raises(ValidationError):
        j1.type = "pipeline"  # type: ignore
