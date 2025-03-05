"""Test the job for making directories"""

import logging
import os

import pyantz.run
from pyantz.infrastructure.config.base import PipelineConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status
from pyantz.jobs.file.make_dirs import make_dirs

test_logger = logging.getLogger(__name__)
test_logger.setLevel(0)


def test_make_dir_exist_ok_true(tmpdir):
    """Test make_dirs with exist_ok=True"""

    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": True}

    status = make_dirs(parameters, test_logger)
    assert status == Status.SUCCESS
    assert os.path.exists(path)
    status = make_dirs(parameters, test_logger)
    assert status == Status.SUCCESS
    assert os.path.exists(path)
    status = make_dirs(parameters, test_logger)
    assert status == Status.SUCCESS
    assert os.path.exists(path)


def test_make_dir_exist_ok_false(tmpdir):
    """Test make_dirs with exist_ok=False"""

    path = os.path.join(tmpdir, "test_dir")

    parameters = {"path": path, "exist_ok": False}

    status = make_dirs(parameters, test_logger)
    assert status == Status.SUCCESS
    status = make_dirs(parameters, test_logger)
    assert status == Status.ERROR
    status = make_dirs(parameters, test_logger)
    assert status == Status.ERROR


def test_success_in_pipeline(tmpdir) -> None:
    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": True}

    job_config = {
        "type": "job",
        "parameters": parameters,
        "function": "pyantz.jobs.file.make_dirs.make_dirs",
    }

    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )

    status = run_pipeline(
        pipeline_config, {}, lambda *args: None, logging.getLogger("test")
    )
    assert status == Status.SUCCESS
    assert os.path.exists(path)

    status = run_pipeline(
        pipeline_config, {}, lambda *args: None, logging.getLogger("test")
    )
    assert status == Status.SUCCESS
    assert os.path.exists(path)

    status = run_pipeline(
        pipeline_config, {}, lambda *args: None, logging.getLogger("test")
    )
    assert status == Status.SUCCESS
    assert os.path.exists(path)


def test_error_in_pipeline(tmpdir) -> None:
    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": False}

    job_config = {
        "type": "job",
        "parameters": parameters,
        "function": "pyantz.jobs.file.make_dirs.make_dirs",
    }

    pipeline_config = PipelineConfig.model_validate(
        {"type": "pipeline", "stages": [job_config]}
    )
    status = run_pipeline(
        pipeline_config, {}, lambda *args: None, logging.getLogger("test")
    )
    assert status == Status.SUCCESS
    assert os.path.exists(path)

    status = run_pipeline(
        pipeline_config, {}, lambda *args: None, logging.getLogger("test")
    )
    assert status == Status.ERROR
    assert os.path.exists(path)

    status = run_pipeline(
        pipeline_config, {}, lambda *args: None, logging.getLogger("test")
    )
    assert status == Status.ERROR
    assert os.path.exists(path)


def test_submit_to_local(tmpdir) -> None:
    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": True}

    job_config = {
        "type": "job",
        "parameters": parameters,
        "function": "pyantz.jobs.file.make_dirs.make_dirs",
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
