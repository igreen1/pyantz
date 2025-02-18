"""Test the job for making directories"""
import os

import logging
from pyantz.jobs.file.make_dirs import make_dirs

from pyantz.infrastructure.core.status import Status
test_logger = logging.getLogger(__name__)
test_logger.setLevel(0)

def test_make_dir_exist_ok_true(tmpdir):
    """Test make_dirs with exist_ok=True"""
    from pyantz.jobs.file.make_dirs import make_dirs

    from pyantz.infrastructure.core.status import Status

    path = os.path.join(tmpdir, "test_dir")

    parameters = {"path": path, "exist_ok": True}

    status = make_dirs(parameters, test_logger)
    assert status == Status.SUCCESS
    status = make_dirs(parameters, test_logger)
    assert status == Status.SUCCESS
    status = make_dirs(parameters, test_logger)
    assert status == Status.SUCCESS

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