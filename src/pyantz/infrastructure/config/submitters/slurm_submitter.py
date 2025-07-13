"""Configuration of the slurm submitter"""

from typing import Literal
import enum

from pydantic import BaseModel, DirectoryPath, Field


class RetryPolicy(enum.StrEnum):
    """Retry policies are how a slurm submitter should try to resubmit jobs that failed

    naive: just resubmit with no changes
    exclude: exclude the node that failed previously
    include: only submit to nodes with previously successful jobs
    current: only submit to the current node
    """

    NAIVE = "naive"
    EXCLUDE = "exclude"
    INCLUDE = "include"
    CURRENT = "current"


class SlurmBasicSubmitter(BaseModel, frozen=True):
    """Configuration of the basic slurm submitter (basic_slurm)

    Fields:
    - type (str): always set to slurm basic
    - name (str): whatever name you want for the submitters
    - max_submit_retries (int): when submitting, how many times to retry a failed submission
        useful if you think the failure is from random node issues
        defaults to 0
    - retry policy: see RetryPolicy enum docstring
        how a submitter should resubmit failed jobs
        defaults to NAIVE
    - submit_wait_time (int): how long after submitting to wait for job fail/success
        in seconds
        defaults to 3
    - slurm_command (str): the command to use to submit. for now, must be sbatch
        in the future, could come up with an srun solution
    """

    type: Literal["slurm_basic"]
    name: str = "basic slurm submitter"
    max_submit_retries: int = 0
    retry_policy: RetryPolicy = RetryPolicy.NAIVE
    submit_wait_time: int = 3
    slurm_command: Literal["sbatch"] = "sbatch"
    working_directory: DirectoryPath
    grid_cmd_args: list[str] = Field(..., default_factory=lambda: [])  # type: ignore
