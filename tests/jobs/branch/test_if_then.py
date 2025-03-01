"""Test the if then branching job"""

import logging
import queue

from pyantz.infrastructure.config.base import PipelineConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status


def return_given(b: bool) -> bool:
    """Return the value provided as an arg"""
    return b


def test_if_then_true_in_pipeline_true() -> None:
    """Test if then running in pipeline"""

    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "submitter_job",
                "function": "pyantz.jobs.branch.if_then.if_then",
                "parameters": {
                    "function": "tests.jobs.branch.test_if_then.return_given",
                    "args": ["%{a}"],
                    "if_true": {
                        "type": "pipeline",
                        "stages": [
                            {
                                "type": "job",
                                "name": "true",
                                "function": "pyantz.jobs.nop.nop",
                                "parameters": {},
                            }
                        ],
                    },
                    "if_false": {
                        "type": "pipeline",
                        "stages": [
                            {
                                "type": "job",
                                "name": "false",
                                "function": "pyantz.jobs.nop.nop",
                                "parameters": {},
                            }
                        ],
                    },
                },
            }
        ],
    }

    q = queue.Queue()

    def submit_fn(p1) -> None:
        q.put(p1)

    assert (
        run_pipeline(
            PipelineConfig.model_validate(pipeline_config),
            {"a": True},
            submit_fn,
            logging.getLogger("test"),
        )
        == Status.FINAL
    )

    assert q.qsize() == 1

    ret = q.get()
    assert ret.config.stages[0].name == "true"


def test_if_then_true_in_pipeline_false() -> None:
    """Test if then running in pipeline"""

    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "submitter_job",
                "function": "pyantz.jobs.branch.if_then.if_then",
                "parameters": {
                    "function": "tests.jobs.branch.test_if_then.return_given",
                    "args": ["%{a}"],
                    "if_true": {
                        "type": "pipeline",
                        "stages": [
                            {
                                "type": "job",
                                "name": "true",
                                "function": "pyantz.jobs.nop.nop",
                                "parameters": {},
                            }
                        ],
                    },
                    "if_false": {
                        "type": "pipeline",
                        "stages": [
                            {
                                "type": "job",
                                "name": "false",
                                "function": "pyantz.jobs.nop.nop",
                                "parameters": {},
                            }
                        ],
                    },
                },
            }
        ],
    }

    q = queue.Queue()

    def submit_fn(p1) -> None:
        q.put(p1)

    assert (
        run_pipeline(
            PipelineConfig.model_validate(pipeline_config),
            {"a": False},
            submit_fn,
            logging.getLogger("test"),
        )
        == Status.FINAL
    )

    assert q.qsize() == 1

    ret = q.get()
    assert ret.config.stages[0].name == "false"
