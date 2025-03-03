"""Test asserting variables"""

import logging

from pyantz.infrastructure.config.base import PipelineConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status


def test_assert_error() -> None:
    """Assert that if non equal the variables are not equal an error is raised"""

    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "job",
                "function": "pyantz.jobs.variables.assert_variable.assert_value",
                "parameters": {"given_val": "%{a}", "expected_value": 2},
            },
        ],
    }

    assert (
        run_pipeline(
            PipelineConfig.model_validate(pipeline_config),
            {"a": 1},
            lambda _: None,
            logging.getLogger("test"),
        )
        == Status.ERROR
    )


def test_assert_success() -> None:
    """Assert that if equal the variables are equal no error is raised"""

    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "job",
                "function": "pyantz.jobs.variables.assert_variable.assert_value",
                "parameters": {"given_val": "%{a}", "expected_value": 2},
            },
        ],
    }

    assert (
        run_pipeline(
            PipelineConfig.model_validate(pipeline_config),
            {"a": 2},
            lambda _: None,
            logging.getLogger("test"),
        )
        == Status.SUCCESS
    )
