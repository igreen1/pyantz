"""Test the explode pipelines job."""

import logging
import queue

from pyantz.infrastructure.config.base import (
    Config,
    InitialConfig,
    ParametersType,
    PipelineConfig,
)
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status
from pyantz.jobs.branch.explode_pipeline import explode_pipeline
from pyantz.run import run


def test_explode_pipelines_job_standalone() -> None:
    """Test calling explode pipelines directly."""
    # Create a queue to store submitted pipelines
    submitted_pipelines = queue.Queue()

    # Create a mock submit function
    def mock_submit_fn(config: Config) -> None:
        submitted_pipelines.put(config)

    # Define parameters and variables
    parameters: ParametersType = {
        "num_pipelines": 3,
        "pipeline_config_template": {
            "type": "pipeline",
            "name": "test_pipeline",
            "stages": [],
        },
    }

    # Call the explode_pipeline function
    status = explode_pipeline(
        parameters,
        mock_submit_fn,
        {},
        PipelineConfig.model_validate({"type": "pipeline", "stages": []}),
        logging.getLogger("test"),
    )

    # Check the status
    assert status == Status.FINAL

    # Check that the correct number of pipelines were submitted
    assert submitted_pipelines.qsize() == 3

    # Check that the submitted pipelines have the correct variables
    for i in range(3):
        config = submitted_pipelines.get()
        assert config.variables["PIPELINE_ID"] == i
        assert config.config.name == "test_pipeline"


def test_explode_pipelines_job_with_pipeline_config() -> None:
    """Test calling explode inside a pipeline config."""
    # Create a queue to store submitted pipelines
    submitted_pipelines = queue.Queue()

    # Create a mock submit function
    def mock_submit_fn(config: Config) -> None:
        submitted_pipelines.put(config)

    # Define parameters and variables
    parameters: ParametersType = {
        "num_pipelines": 3,
        "pipeline_config_template": {
            "type": "pipeline",
            "name": "test_pipeline",
            "stages": [],
        },
    }

    pipeline_config = PipelineConfig.model_validate(
        {
            "type": "pipeline",
            "stages": [
                {
                    "type": "submitter_job",
                    "function": "pyantz.jobs.branch.explode_pipeline.explode_pipeline",
                    "parameters": parameters,
                }
            ],
        }
    )

    status = run_pipeline(
        pipeline_config,
        {},
        mock_submit_fn,
        logging.getLogger("test"),
    )

    # Check the status
    assert status == Status.FINAL

    # Check that the correct number of pipelines were submitted
    assert submitted_pipelines.qsize() == 3

    # Check that the submitted pipelines have the correct variables
    for i in range(3):
        config = submitted_pipelines.get()
        assert config.variables["PIPELINE_ID"] == i
        assert config.config.name == "test_pipeline"


def test_explode_pipelines_job_in_local_submitter() -> None:
    """Test exploding the pipelines integrated with the local submitter."""
    # Define parameters and variables
    parameters: ParametersType = {
        "num_pipelines": 3,
        "pipeline_config_template": {
            "type": "pipeline",
            "name": "test_pipeline",
            "stages": [],
        },
    }

    pipeline_config = PipelineConfig.model_validate(
        {
            "type": "pipeline",
            "stages": [
                {
                    "type": "submitter_job",
                    "function": "pyantz.jobs.branch.explode_pipeline.explode_pipeline",
                    "parameters": parameters,
                }
            ],
        }
    )

    config = InitialConfig.model_validate(
        {
            "submitter_config": {"type": "local"},
            "analysis_config": {
                "variables": {},
                "config": pipeline_config,
            },
        }
    )

    run(config)
