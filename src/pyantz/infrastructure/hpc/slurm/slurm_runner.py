"""Runs configurations on a slurm grid"""

from .restful.models.job_submit_req import JobSubmitReq
from .restful.models.job_desc_msg import JobDescMsg
from pyantz.infrastructure.config.base import Config, InitialConfig, LoggingConfig
from pyantz.infrastructure.core.manager import run_manager
from pyantz.infrastructure.log.multiproc_logging import ANTZ_LOG_ROOT_NAME, get_listener
import argparse
import json


def run_slurm_submitter(config: InitialConfig) -> None:
    """Start a slurm submitter and create the pipelines for the jobs"""


    """
    Submit a job,
        that job will then enqueue more jobs to submit
    Those jobs will then be submitted
    """


# def _submit_a_job_to_grid(original_config: InitialConfig, next_config: Config) -> None:


def _run_job_on_grid_from_file_config(config_path: str) -> None:

    with open(config_path, 'r') as fh:
        config = JobSubmitReq.model_validate_json(fh.read())

    _run_job_on_grid_from_config(config)

if __name__ == '__main__':
    # this is run when a slurm job is submitted

    parser = argparse.ArgumentParser(
        prog='Pyantz Slurm'
    )
    parser.add_argument(
        "-c", "--config", required=True, help="Path to a config file to run"
    )

    config_path: str = parser.parse_args().config

    _run_job_on_grid_from_file_config(config_path)
