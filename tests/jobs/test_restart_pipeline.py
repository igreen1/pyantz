"""Test restart pipeline job."""

import logging
import queue

from pyantz.infrastructure.config.base import Config, PipelineConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status


def test_restarting_a_pipeline() -> None:
    """Test that the job can restart a pipeline."""
    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "submitter_job",
                "function": "pyantz.jobs.restart_pipeline.restart_pipeline",
                "parameters": {},
            }
        ],
    }

    q = queue.Queue()

    def submit_fn(config: Config) -> None:
        q.put(config)

    run_pipeline(
        PipelineConfig.model_validate(pipeline_config),
        {},
        submit_fn,
        logging.getLogger("test"),
    ) == Status.FINAL

    assert q.qsize() == 1
    config = q.get()
    assert config.config.curr_stage == 0


def test_restarting_a_pipeline_conditional_true() -> None:
    """Test that the job can restart a pipeline."""
    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "submitter_job",
                "function": "pyantz.jobs.restart_pipeline.restart_pipeline",
                "parameters": {"left": "%{a}", "comparator": "<", "right": 4},
            }
        ],
    }

    q = queue.Queue()

    def submit_fn(config: Config) -> None:
        q.put(config)

    run_pipeline(
        PipelineConfig.model_validate(pipeline_config),
        {"a": 1},
        submit_fn,
        logging.getLogger("test"),
    ) == Status.FINAL

    assert q.qsize() == 1
    config = q.get()
    assert config.config.curr_stage == 0


def test_restarting_a_pipeline_conditional_false() -> None:
    """Test that the job can restart a pipeline."""
    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "submitter_job",
                "function": "pyantz.jobs.restart_pipeline.restart_pipeline",
                "parameters": {"left": "%{a}", "comparator": ">", "right": 4},
            }
        ],
    }

    q = queue.Queue()

    def submit_fn(config: Config) -> None:
        q.put(config)

    run_pipeline(
        PipelineConfig.model_validate(pipeline_config),
        {"a": 1},
        submit_fn,
        logging.getLogger("test"),
    ) == Status.FINAL

    assert q.qsize() == 0
