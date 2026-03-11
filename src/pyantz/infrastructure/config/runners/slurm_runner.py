"""Slurm runner runs on a slurm HPC grid."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, DirectoryPath, Field

DEFAULT_JOB_TIMEOUT: int = 10_000  # 2-ish hours


class SlurmRunnerConfig(BaseModel):
    """Configuration used by the slurm submitters."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["slurm_sbatch"] = "slurm_sbatch"

    # max time a job can be running before slurm timeouts
    max_job_time_seconds: int = DEFAULT_JOB_TIMEOUT

    slurm_args: list[str] = Field(default_factory=list)

    working_dir: DirectoryPath
