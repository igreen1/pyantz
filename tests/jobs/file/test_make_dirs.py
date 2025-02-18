"""Test the job for making directories"""
import os

import logging
from pyantz.jobs.file.make_dirs import make_dirs

from pyantz.infrastructure.core.status import Status
from tests.jobs.generic_job_tester import success_in_pipeline, error_in_pipeline, submit_to_local

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
        'function': 'pyantz.jobs.file.make_dirs.make_dirs'
    }

    success_in_pipeline(job_config)
    assert os.path.exists(path)
    success_in_pipeline(job_config)
    assert os.path.exists(path)
    success_in_pipeline(job_config)
    assert os.path.exists(path)

def test_error_in_pipeline(tmpdir) -> None:
    

    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": False}

    job_config = {
        "type": "job",
        "parameters": parameters,
        'function': 'pyantz.jobs.file.make_dirs.make_dirs'
    }

    success_in_pipeline(job_config)
    assert os.path.exists(path)
    error_in_pipeline(job_config)
    assert os.path.exists(path)
    error_in_pipeline(job_config)
    assert os.path.exists(path)


def submit_to_local(tmpdir) -> None:
    

    path = os.path.join(tmpdir, "test_dir")
    parameters = {"path": path, "exist_ok": True}

    job_config = {
        "type": "job",
        "parameters": parameters,
        'function': 'pyantz.jobs.file.make_dirs.make_dirs'
    }

    submit_to_local(job_config)
    assert os.path.exists(path)
    submit_to_local(job_config)
    assert os.path.exists(path)
    submit_to_local(job_config)
    assert os.path.exists(path)