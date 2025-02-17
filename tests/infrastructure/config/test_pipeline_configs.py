"""Test the creation of a pipeline configuration"""

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config.base import JobConfig, PipelineConfig
from pyantz.infrastructure.core.status import Status


def fake_job_task(parameters, *args) -> Status:
    """Return success only if arg1 is passed as 1"""
    if parameters["arg1"] == 1:
        return Status.SUCCESS
    return Status.ERROR


def test_create_pipeline_config() -> None:
    """Create a simple pipeline configuration"""

    pipeline_config = {"type": "pipeline", "name": "my pipeline", "stages": []}
    p1 = PipelineConfig.model_validate(pipeline_config)

    assert p1.curr_stage == 0
    assert p1.status == Status.READY
    assert p1.max_allowed_restarts == 0
    assert p1.curr_restarts == 0
    assert p1.stages == []


def test_pipeline_with_job_config() -> None:
    """Test a pipeline with a job inside it"""
    pipeline_config = {
        "type": "pipeline",
        "name": "my pipeline",
        "stages": [
            {
                "type": "job",
                "name": "my job",
                "function": "tests.infrastructure.config.test_pipeline_configs.fake_job_task",
                "parameters": {"arg1": 1, "arg2": 2},
            }
        ],
    }
    p1 = PipelineConfig.model_validate(pipeline_config)

    assert isinstance(p1.stages[0], JobConfig)
    assert p1.stages[0].function == fake_job_task


def test_disallow_nested_pipeline() -> None:
    """Test a pipeline config with apipeline inside of it"""

    pipeline_config = {
        "type": "pipeline",
        "name": "my pipeline",
        "stages": [
            {
                "type": "pipeline",
                "name": "sub pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "my job",
                        "function": "tests.infrastructure.config.test_pipeline_configs.fake_job_task",
                        "parameters": {"arg1": 1, "arg2": 2},
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValidationError):
        PipelineConfig.model_validate(pipeline_config)
