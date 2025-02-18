"""Provides a generalized way to test a job"""
from pyantz.infrastructure.config.base import PipelineConfig
from pyantz.infrastructure.core.status import Status
from pyantz.infrastructure.core.pipeline import run_pipeline
import pyantz.run
import logging

def submit_to_local(job_config) -> None:
    """Test a job that can be put onto the submission pipeline"""
    from pyantz.infrastructure.core.status import Status

    test_config = {
        "submitter_config": {"type": "local"},
        "analysis_config": {
            "variables": {},
            "config": {
                'type': 'pipeline',
                'stages': [job_config]
            }
        }
    }
    pyantz.run.run(test_config)

def success_in_pipeline(job_config) -> None:

    pipeline_config = PipelineConfig.model_validate({
        'type': 'pipeline',
        'stages': [job_config]
    })
    status = run_pipeline(pipeline_config, {}, lambda *args: None, logging.getLogger('test'))

    assert status == Status.SUCCESS


def error_in_pipeline(job_config) -> None:

    pipeline_config = PipelineConfig.model_validate({
        'type': 'pipeline',
        'stages': [job_config]
    })
    status = run_pipeline(pipeline_config, {}, lambda *args: None, logging.getLogger('test'))

    assert status == Status.ERROR