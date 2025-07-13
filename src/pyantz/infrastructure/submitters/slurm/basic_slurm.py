"""The SLURM restful API is a pain to code
This will instead use SBATCH and rely a bit more on user knowledge of the commands

A "manager" will start up in the job, which will then run the requested job
Then, it will submit the next job. TO submit
    1. create a uuid for the next jobn
    2. create a json for the next job
    3. save the json to the working directory with name of the uuid
    4. sbatch with the uuid

"""

import argparse
import os
import uuid
import subprocess
import logging
import re
import stat
from textwrap import dedent

from pyantz.infrastructure.config.submitters.slurm_submitter import SlurmBasicSubmitter
from pyantz.infrastructure.config.base import Config, InitialConfig
from pyantz.infrastructure.core.manager import run_manager
from pyantz.infrastructure.log.multiproc_logging import ANTZ_LOG_ROOT_NAME

SBATCH_RETURN: re.Pattern = re.compile(r"Submitted batch job (\d+)")


def run_slurm_local(initial_config: InitialConfig) -> None:
    """Run the submitted job locally (on this node)"""

    if not isinstance(initial_config.submitter_config, SlurmBasicSubmitter):
        raise ValueError('Cannot "run_slurm_local" with non slurm configuration')

    def submit_next(config: Config) -> None:
        """Closure to wrap the config in a new initial config and write it out"""
        rewrapped_config = InitialConfig(
            analysis_config=config,
            submitter_config=initial_config.submitter_config,
            logging_config=initial_config.logging_config,
        )
        # now, actually submit that job, retrying if it fails too quickly
        for _attempt in range(
            initial_config.submitter_config.max_submit_retries + 1  # type: ignore
        ):
            if _submit_job_to_grid(rewrapped_config):
                break

    logger = logging.getLogger(ANTZ_LOG_ROOT_NAME + ".slurm_logger")
    run_manager(initial_config.analysis_config, submit_fn=submit_next, logger=logger)


def _submit_job_to_grid(config: InitialConfig) -> bool:
    """Submit the next job to the grid"""
    if not isinstance(config.submitter_config, SlurmBasicSubmitter):
        raise ValueError(
            "ERROR: Slurm invoked when submitter config not slurm_basic type"
        )

    job_uuid: uuid.UUID = uuid.uuid4()

    if config.submitter_config.slurm_command != "sbatch":
        raise ValueError("Only SBATCH currently supported")

    # create the sbatch file
    sbatch_file: str = dedent(f"""#!/bin/bash
    python {__file__} ${{1}}
    """)
    sbatch_file_path: str = os.path.join(
        config.submitter_config.working_directory, f"{job_uuid}_submit.sh"
    )

    with open(sbatch_file_path, "w", encoding="utf-8") as fh:
        fh.write(sbatch_file)
    os.chmod(sbatch_file_path, stat.S_IXGRP | stat.S_IXUSR | stat.S_IXOTH)

    # write out the configuration
    config_file_path: str = os.path.join(
        config.submitter_config.working_directory, f"{job_uuid}_config.json"
    )
    with open(config_file_path, "w", encoding="utf-8") as fh:
        fh.write(config.model_dump_json())
    os.chmod(config_file_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    sbatch_cmd = [
        "sbatch",
        *config.submitter_config.grid_cmd_args,
        sbatch_file_path,
        "-c",
        config_file_path,
    ]

    # now actually perform the sbatch
    sbatch_result = subprocess.run(
        sbatch_cmd,
        check=True,
        stdout=subprocess.PIPE,
    )

    sbatch_match = SBATCH_RETURN.match(sbatch_result.stdout.decode())
    if sbatch_match is None:
        raise ValueError(
            "Unable to monitor job - could not get job id from sbatch return"
        )

    job_id = int(sbatch_match.group(1))

    return _get_sbatch_status(job_id, config.submitter_config.submit_wait_time)


def _get_sbatch_status(job_id: int, max_wait_time: int) -> bool:  # pylint: disable=unused-argument
    """Return true if the job shows up in squeue

    TODO: setup sacct and use that to check if its available
    """
    # TODO: implement # pylint: disable=fixme
    return True


def _main(config_path: str) -> None:
    """Invoked when a new job spawns on a node"""

    with open(config_path, "r", encoding="utf-8") as config_file_handle:
        job_config = InitialConfig.model_validate_json(config_file_handle.read())

    run_slurm_local(job_config)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-c", "--config", required=True, help="Configuration file to run"
    )

    args = arg_parser.parse_args()
    _main(args.config)
