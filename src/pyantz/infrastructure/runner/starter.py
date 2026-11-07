"""Startup our program.

Check if we're in the right execution environment,
the point to the correct local runner.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pyantz.infrastructure.config import InitialConfig as _InitialConfig
from pyantz.infrastructure.runner import start_local as _start_local
from pyantz.infrastructure.runner.slurm import start as _start_slurm

from ._remotes.container import run_container as start_container
from ._remotes.ssh import run_ssh as start_ssh

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyantz.infrastructure.distributed_queue.common.return_types import JobsReport


def start(config: _InitialConfig | Mapping[str, Any]) -> JobsReport | None:
    """Check how to start the program and route to the proper starter.

    This is the main entry point of pyantz, also available as ``pyantz.start``.

    Args:
        config: the pipeline's configuration, as an
            :class:`~pyantz.infrastructure.config.InitialConfig` or a mapping
            (e.g., loaded from JSON) describing one.

    Returns:
        JobsReport | None: final report of the jobs when the run is local and
            blocking; None if the outcome is not known (e.g. remote hosts).

    Raises:
        pydantic.ValidationError: if the configuration is invalid.
        ValueError: if the submitter type is unknown.

    Example:
        .. testsetup:: runner-start

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: runner-start

            from pyantz import start

            report = start(
                {
                    "submitter": {"type_": "local_proc", "working_directory": "."},
                    "jobs": [
                        {
                            "job_id": "make",
                            "function": "pyantz.jobs.files.simple.create",
                            "parameters": {"path": "out.txt", "contents": "hi"},
                        },
                        {
                            "function": "pyantz.jobs.files.check.file_contains",
                            "parameters": {"file": "out.txt", "substring": "hi"},
                            "depends_on": ["make"],
                        },
                    ],
                }
            )
            print(report.total, report.success, report.all_succeeded)

        .. testoutput:: runner-start

            2 2 True

        .. testcleanup:: runner-start

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    logger = logging.getLogger(__name__)
    loaded_config: _InitialConfig = _InitialConfig.model_validate(config)
    logger.debug(
        "Validated configuration with %d job(s), host %s, submitter %s",
        len(loaded_config.jobs),
        loaded_config.host.type_,
        loaded_config.submitter.type_,
    )
    if loaded_config.host.type_ == "local":
        return run_local(loaded_config)
    if loaded_config.host.type_ == "container":
        start_container(loaded_config)
        return None
    if loaded_config.host.type_ == "ssh":
        start_ssh(loaded_config)
        return None

    return None


def run_local(config: _InitialConfig) -> JobsReport | None:
    """Start running the various jobs.

    This is a blocking operation if running locally.

    Args:
        config: the validated configuration, whose host is this machine.

    Returns:
        JobsReport | None: final report of the jobs for the local runner; None for
        slurm, whose jobs run after this returns.

    Raises:
        ValueError: if the submitter type is unknown.

    Example:
        .. testsetup:: runner-run-local

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: runner-run-local

            from pyantz.infrastructure.config import InitialConfig
            from pyantz.infrastructure.runner.starter import run_local

            config = InitialConfig.model_validate(
                {
                    "submitter": {
                        "type_": "local_proc",
                        "working_directory": ".",
                        "use_same_proc": True,
                    },
                    "jobs": [
                        {
                            "function": "pyantz.jobs.files.check.file_exists",
                            "parameters": {"file": "missing.txt"},
                        },
                    ],
                }
            )
            report = run_local(config)
            print(report.error, report.all_succeeded)

        .. testoutput:: runner-run-local

            1 False

        .. testcleanup:: runner-run-local

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    logging.getLogger(__name__).debug(
        "Starting %s submitter on this machine",
        config.submitter.type_,
    )
    # if not loaded, check it
    if config.submitter.type_ == "local_proc":
        # start local runner
        return _start_local(config)
    if config.submitter.type_ == "slurm_sbatch":
        _start_slurm(config)
        return None
    msg = f"Unknown submitter type: {config.submitter.type_!r}"
    raise ValueError(msg)
