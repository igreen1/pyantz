"""Test the compare job"""

import logging
import os
import queue
import shutil

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
                "name": "true",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "name": "false",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }
    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    q = queue.Queue()
    def submit_fn(job_config):
        q.put(job_config)

    status = run_pipeline(pipeline_config, {}, submit_fn, logging.getLogger("test"))

    assert status == Status.FINAL
    assert q.qsize() == 1
    next_Job = q.get()
    assert next_Job.config.name == "true"


def test_false_direct_comparison() -> None:
    """Test that a comparison that is false returns the false pipeline"""

    job_config = {
        "type": "submitter_job",
        "parameters": {
            "comparator": "==",
            "left": 1,
            "right": 2,
            "if_true": {
                "type": "pipeline",
                "name": "true",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "name": "false",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }
    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    q = queue.Queue()
    def submit_fn(job_config):
        q.put(job_config)

    status = run_pipeline(pipeline_config, {}, submit_fn, logging.getLogger("test"))

    assert status == Status.FINAL
    assert q.qsize() == 1
    next_Job = q.get()
    assert next_Job.config.name == "false"


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
                "name": "true",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "name": "false",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }
    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    q = queue.Queue()
    def submit_fn(job_config):
        q.put(job_config)

    status = run_pipeline(
        pipeline_config, {"my_var1": 0}, submit_fn, logging.getLogger("test")
    )

    assert status == Status.FINAL
    assert q.qsize() == 1
    next_job = q.get()
    assert next_job.config.name == "true"


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
                "name": "true",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "name": "false",
                "stages": [
                    {
                        "type": "job",
                        "name": "false",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }
    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    q = queue.Queue()
    def submit_fn(job_config):
        q.put(job_config)

    status = run_pipeline(
        pipeline_config, {"my_var1": 0}, submit_fn, logging.getLogger("test")
    )

    assert status == Status.FINAL
    assert q.qsize() == 1
    next_job = q.get()
    assert next_job.config.name == "false"


def test_submit_to_local(tmpdir) -> None:

    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": True}

    job_config = {
        "type": "submitter_job",
        "parameters": {
            "comparator": "==",
            "left": 5,
            "right": "%{my_var1+4}",
            "if_true": {
                "type": "pipeline",
                "name": "true",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": parameters,
                        "function": "pyantz.jobs.file.make_dirs.make_dirs",
                    }
                ],
            },
            "if_false": {
                "type": "pipeline",
                "name": "false",
                "stages": [
                    {
                        "type": "job",
                        "name": "true",
                        "parameters": {**parameters, "exist_ok": False},
                        "function": "pyantz.jobs.file.make_dirs.make_dirs",
                    }
                ],
            },
        },
        "function": "pyantz.jobs.branch.compare.compare",
    }

    test_config = {
        "submitter_config": {"type": "local"},
        "analysis_config": {
            "variables": {
                "my_var1": 1,
            },
            "config": {"type": "pipeline", "stages": [job_config]},
        },
    }
    pyantz.run.run(test_config)
    os.path.exists(path)
    pyantz.run.run(test_config)
    os.path.exists(path)
    shutil.rmtree(path)
    pyantz.run.run(test_config)
    os.path.exists(path)
