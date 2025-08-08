"""Test setting variables from a function."""

import logging
import queue
from typing import TypeVar

from pyantz.infrastructure.config.base import Config, PipelineConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status

T = TypeVar("T")


def function_[T](arg1: T) -> T:
    """Return the provided argument."""
    return arg1


def test_set_variable_from_function() -> None:
    """Test setting a variable from a function."""
    q = queue.Queue()

    def submit_fn(config: Config) -> None:
        q.put(config)

    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "mutable_job",
                "function": "pyantz.jobs.variables.set_variable_from_function.set_variable_from_function",
                "parameters": {
                    "left_hand_side": "a",
                    "right_hand_side": "tests.jobs.variables.test_set_variables_from_function.function_",
                    "args": [1],
                },
            },
            {"type": "job", "function": "pyantz.jobs.nop.nop", "parameters": {}},
        ],
    }

    assert (
        run_pipeline(
            PipelineConfig.model_validate(pipeline_config),
            {},
            submit_fn,
            logging.getLogger(),
        )
        == Status.SUCCESS
    )

    assert q.qsize() == 1
    config = q.get()
    assert config.variables == {"a": 1}
