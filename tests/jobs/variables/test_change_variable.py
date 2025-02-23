"""Change variables in a pipeline"""

import logging
import os
import queue

import pytest

import pyantz.run
from pyantz.infrastructure.config.base import PipelineConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status


def test_changing_variables(tmpdir) -> None:
    """Test that subsequent jobs can access mutated variables"""

    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "mutable_job",
                "function": "pyantz.jobs.variables.change_variable.change_variable",
                "name": "change_variable",
                "parameters": {
                    "left_hand_side": "a",
                    "right_hand_side": "my_dir",
                },
            },
            {
                "type": "simple_job",
                "function": "pyantz.jobs.file.make_dirs.make_dirs",
                "parameters": {"path": os.fspath(tmpdir) + os.sep + "%{a}"},
            },
        ],
    }

    q = queue.Queue()

    def submit_fn(config) -> None:
        q.put(config)

    run_pipeline(
        PipelineConfig.model_validate(pipeline_config),
        {},
        submit_fn,
        logging.getLogger("test"),
    )

    assert q.qsize() == 1

    ret_config = q.get()
    assert ret_config.variables == {
        "a": "my_dir",
    }


def test_changing_variables_integrated(tmpdir) -> None:
    """Test that subsequent jobs can access mutated variables"""

    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "mutable_job",
                "function": "pyantz.jobs.variables.change_variable.change_variable",
                "name": "change_variable",
                "parameters": {
                    "left_hand_side": "a",
                    "right_hand_side": "my_dir",
                },
            },
            {
                "type": "simple_job",
                "function": "pyantz.jobs.file.make_dirs.make_dirs",
                "parameters": {"path": os.fspath(tmpdir) + os.sep + "%{a}"},
            },
        ],
    }

    # submit to a local submitter to run the pipeline to completion
    config = {
        "submitter_config": {"type": "local"},
        "analysis_config": {"variables": {}, "config": pipeline_config},
    }
    pyantz.run.run(config)

    assert (
        run_pipeline(
            PipelineConfig.model_validate(pipeline_config),
            {},
            lambda x: None,
            logging.getLogger("test"),
        )
        == Status.SUCCESS
    )

    assert os.path.exists(os.path.join(tmpdir, "my_dir"))


def test_changing_variables_bad_variable(tmpdir) -> None:
    """Test that subsequent jobs can access mutated variables"""

    pipeline_config = {
        "type": "pipeline",
        "stages": [
            {
                "type": "mutable_job",
                "function": "pyantz.jobs.variables.change_variable.change_variable",
                "name": "change_variable",
                "parameters": {
                    "left_hand_side": "a",
                },
            },
        ],
    }

    with pytest.raises(ValueError):
        PipelineConfig.model_validate(pipeline_config)
