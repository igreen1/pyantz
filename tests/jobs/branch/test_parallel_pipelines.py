"""Test the ability to split and create abitrary parallel pipelines"""

import logging
import queue

from pyantz.infrastructure.config.base import Config, PipelineConfig, SubmitterJobConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status


def test_parallel_pipelines_in_pipeline() -> None:
    """Test splitting and creating two pipelines"""

    p1 = PipelineConfig.model_validate(
        {
            "type": "pipeline",
            "name": "pipeline_uno",
            "stages": [
                {"type": "job", "function": "pyantz.jobs.nop.nop", "parameters": None}
            ],
        }
    )
    p2 = PipelineConfig.model_validate(
        {
            "type": "pipeline",
            "name": "pipeline_dos",
            "stages": [
                {"type": "job", "function": "pyantz.jobs.nop.nop", "parameters": None}
            ],
        }
    )
    j2 = SubmitterJobConfig.model_validate(
        {
            "type": "submitter_job",
            "function": "pyantz.jobs.branch.parallel_pipelines.parallel_pipelines",
            "parameters": {"pipelines": [p1, p2]},
        }
    )
    config = {"type": "pipeline", "stages": [j2]}

    q: queue.Queue = queue.Queue()

    def submit_fn(config) -> None:
        q.put(config.model_dump())

    p_config = PipelineConfig.model_validate(config)

    assert (
        run_pipeline(p_config, {}, submit_fn, logging.getLogger("test")) == Status.FINAL
    )

    assert q.qsize() == 2
    ret1 = Config.model_validate(q.get())
    ret2 = Config.model_validate(q.get())

    assert ret1.config.name == "pipeline_uno" or ret2.config.name == "pipeline_uno"
    assert ret1.config.name == "pipeline_dos" or ret2.config.name == "pipeline_dos"
