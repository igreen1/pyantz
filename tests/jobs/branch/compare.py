"""Test the compare job"""

import logging
import os
import queue

import pyantz.run
from pyantz.infrastructure.config.base import PipelineConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status


def test_true_comparison() -> None:
    """Test that a comparison that is true returns the true pipeline"""

    job_config = {
        "type": "submitter_job",
        "parameters": {
            "comparator": "==",
            "left": 1,
            "right": 1,
            "if_true": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }
    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    queue = queue.Queue()
    submit_fn = lambda job_config: queue.put(job_config)

    status = run_pipeline(pipeline_config, {}, submit_fn, logging.getLogger("test"))

    assert status == Status.SUCCESS
    assert queue.qsize() == 1
    next_Job = queue.get()
    assert next_Job["name"] == "true"


def test_true_comparison() -> None:
    """Test that a comparison that is false returns the false pipeline"""

    job_config = {
        "type": "submitter_job",
        "parameters": {
            "comparator": "==",
            "left": 1,
            "right": 2,
            "if_true": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }
    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    queue = queue.Queue()
    submit_fn = lambda job_config: queue.put(job_config)

    status = run_pipeline(pipeline_config, {}, submit_fn, logging.getLogger("test"))

    assert status == Status.SUCCESS
    assert queue.qsize() == 1
    next_Job = queue.get()
    assert next_Job["name"] == "false"


def test_comparison_with_variables_true() -> None:
    """Test that a comparison that is true returns the true pipeline"""

    job_config = {
        "type": "submitter_job",
        "parameters": {
            "comparator": "==",
            "left": 1,
            "right": "%{my_var1+1}",
            "if_true": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }
    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    queue = queue.Queue()
    submit_fn = lambda job_config: queue.put(job_config)

    status = run_pipeline(
        pipeline_config, {"my_var": 0}, submit_fn, logging.getLogger("test")
    )

    assert status == Status.SUCCESS
    assert queue.qsize() == 1
    next_Job = queue.get()
    assert next_Job["name"] == "true"


def test_comparison_with_variables_false() -> None:
    """Test that a comparison that is false and involves variables returns the false pipeline"""

    job_config = {
        "type": "submitter_job",
        "parameters": {
            "comparator": "==",
            "left": 1,
            "right": "%{my_var1+4}",
            "if_true": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }
    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    queue = queue.Queue()
    submit_fn = lambda job_config: queue.put(job_config)

    status = run_pipeline(
        pipeline_config, {"my_var": 0}, submit_fn, logging.getLogger("test")
    )

    assert status == Status.SUCCESS
    assert queue.qsize() == 1
    next_Job = queue.get()
    assert next_Job["name"] == "true"


def test_submit_to_local(tmpdir) -> None:

    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": True}

    job_config = {
        "type": "submitter_job",
        "parameters": {
            "comparator": "==",
            "left": 1,
            "right": "%{my_var1+4}",
            "if_true": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.generic.no_op.no_op",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }

    test_config = {
        "submitter_config": {"type": "local"},
        "analysis_config": {
            "variables": {},
            "config": {"type": "pipeline", "stages": [job_config]},
        },
    }
    pyantz.run.run(test_config)
    assert os.path.exists(path)
    pyantz.run.run(test_config)
    assert os.path.exists(path)
    pyantz.run.run(test_config)
    assert os.path.exists(path)
