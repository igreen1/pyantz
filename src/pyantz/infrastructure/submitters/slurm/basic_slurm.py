"""Use `sbatch` to submit jobs, which requires users to understand that command.

The SLURM restful API is a pain to code.

A "manager" will start up in the job, which will then run the requested job
Then, it will submit the next job. TO submit
    1. create a uuid for the next jobn
    2. create a json for the next job
    3. save the json to the working directory with name of the uuid
    4. sbatch with the uuid

"""

import argparse
import logging
import os
import pathlib
import re
import stat
import subprocess  # nosec
import uuid
from textwrap import dedent

from pyantz.infrastructure.config.base import Config, InitialConfig
from pyantz.infrastructure.config.submitters.slurm_submitter import SlurmBasicSubmitter
from pyantz.infrastructure.core.manager import run_manager
from pyantz.infrastructure.log.multiproc_logging import ANTZ_LOG_ROOT_NAME

SBATCH_RETURN: re.Pattern[str] = re.compile(r"Submitted batch job (\d+)")


def run_slurm_local(initial_config: InitialConfig) -> None:
    """Run the submitted job locally (on this node)."""
    if not isinstance(initial_config.submitter_config, SlurmBasicSubmitter):
        msg = 'Cannot "run_slurm_local" with non slurm configuration'
        raise TypeError(msg)

    def submit_next(config: Config) -> None:
        """Closure to wrap the config in a new initial config and write it out."""
        rewrapped_config = InitialConfig(
            analysis_config=config,
            submitter_config=initial_config.submitter_config,
            logging_config=initial_config.logging_config,
        )
        # now, actually submit that job, retrying if it fails too quickly
        # need to type hint config as "Config with attribute of type slurm basic submitter"
        # unclear how to do that, so just ignore the error for now
        for _attempt in range(
            initial_config.submitter_config.max_submit_retries + 1  # type: ignore[union-attr]
        ):
            if _submit_job_to_grid(rewrapped_config):
                break

    logger = logging.getLogger(ANTZ_LOG_ROOT_NAME + ".slurm_logger")
    run_manager(initial_config.analysis_config, submit_fn=submit_next, logger=logger)


def _submit_job_to_grid(config: InitialConfig) -> bool:
    """Submit the next job to the grid."""
    if not isinstance(config.submitter_config, SlurmBasicSubmitter):
        msg = "ERROR: Slurm invoked when submitter config not slurm_basic type"
        raise TypeError(msg)

    job_uuid: uuid.UUID = uuid.uuid4()

    if config.submitter_config.slurm_command != "sbatch":
        msg = "Only SBATCH currently supported"
        raise TypeError(msg)

    # create the sbatch file
    sbatch_file: str = dedent(f"""#!/bin/bash
    python {__file__} ${{1}}
    """)
    sbatch_file_path: pathlib.Path = (
        pathlib.Path(config.submitter_config.working_directory) / f"{job_uuid}_submit.sh"
    )
    with sbatch_file_path.open(mode="w", encoding="utf-8") as fh:
        fh.write(sbatch_file)
    sbatch_file_path.chmod(stat.S_IXGRP | stat.S_IXUSR | stat.S_IXOTH)

    # write out the configuration
    config_file_path: pathlib.Path = (
        pathlib.Path(config.submitter_config.working_directory) / f"{job_uuid}_config.json"
    )
    with config_file_path.open(mode="w", encoding="utf-8") as fh:
        fh.write(config.model_dump_json())
    config_file_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    sbatch_cmd: list[str] = [
        "sbatch",
        *config.submitter_config.grid_cmd_args,
        os.fspath(sbatch_file_path),
        "-c",
        os.fspath(config_file_path),
    ]

    # now actually perform the sbatch
    sbatch_result = subprocess.run(  # noqa: S603
        sbatch_cmd,
        check=True,
        stdout=subprocess.PIPE,
    )  # nosec

    sbatch_match = SBATCH_RETURN.match(sbatch_result.stdout.decode())
    if sbatch_match is None:
        msg = "Unable to monitor job - could not get job id from sbatch return"
        raise ValueError(msg)

    job_id = int(sbatch_match.group(1))

    return _get_sbatch_status(job_id, config.submitter_config.submit_wait_time)


def _get_sbatch_status(job_id: int, max_wait_time: int) -> bool:  # pylint: disable=unused-argument # noqa: ARG001
    """Return true if the job shows up in squeue.

    TODO: setup sacct and use that to check if its available
    """
    return True


def _main(config_path: str) -> None:
    """Invoke when a new job spawns on a node."""
    config_path_: pathlib.Path = pathlib.Path(config_path)
    with config_path_.open(mode="r", encoding="utf-8") as config_file_handle:
        job_config = InitialConfig.model_validate_json(config_file_handle.read())

    run_slurm_local(job_config)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-c", "--config", required=True, help="Configuration file to run")

    args = arg_parser.parse_args()
    _main(args.config)
