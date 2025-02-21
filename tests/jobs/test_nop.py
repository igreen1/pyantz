"""Test the nop job. It does nothing so really just testing it doesn't crash"""

from pyantz.jobs.nop import nop
from pyantz.infrastructure.core.status import Status
import logging
from pyantz.infrastructure.config.base import PipelineConfig, InitialConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
import pyantz.run


def test_nop_direct_call() -> None:
    """Test that the nop job does not crash"""

    assert nop({}, logging.getLogger("test")) == Status.SUCCESS

def test_nop_in_pipeline() -> None:
    """Test that the nop job does not crash when in a pipeline"""

    pipeline_config = PipelineConfig.model_validate(
        {
            "type": "pipeline",
            "stages": [
                {
                    "type": "job",
                    "name": "nop",
                    "parameters": {},
                    "function": "pyantz.jobs.nop.nop",
                }
            ],
        }
    )

    status = run_pipeline(pipeline_config, {}, None, logging.getLogger("test"))
    assert status == Status.SUCCESS

def test_submit_to_local() -> None:
    """Test that it doesn't crash when in a submitter job"""
    test_config = InitialConfig.model_validate({
        "submitter_config": { "type": "local" },
        "analysis_config": {
            "variables": {},
            "config": {
            "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "name": "nop",
                        "parameters": {},
                        "function": "pyantz.jobs.nop.nop",
                    }
                ],
            }
        }
    })

    
    pyantz.run.run(test_config)
    pyantz.run.run(test_config)