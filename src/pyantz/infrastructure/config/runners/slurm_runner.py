r"""Slurm runner runs on a slurm HPC grid.

Note, setting `inherit_dependencies=False` creates a slurm submitter
which doesn't inherit dependencies.

Critically, this fully **disallows** inheriting dependencies. For example,
consider the below pipeline

A -> B -> C

If A submits job A1 and A2, we would want B to wait until A1 and A2
have completed. Local and Slurm runner "inherit" this dependency
by modifying B to be dependent on A1 and A2. This is no longer
possible in this situation. Therefore, the run order may be

A -> B -> A1 -> C -> A2

In fact, any ordering of A1 and A2 is possible as they will be unlinked from the
dependency tree and run as children.

Why use this? Some security policies disallow modifying jobs after submitting.
There are a few ways to handle this, but in many cases, a user may not care.

For example, consider the same pipeline but imagine that C was submitting jobs.
It doesn't matter than C will spawn "dependency-less" children, it is the last job.
So any execution order is find for the spawned chains to execute.

SOmething like the below is possible, which fits many use cases.
              C1
            /
A -> B -> C
            \ C2

"""

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

    # if some job A depends on job P and job P submits jobs
    # P1 and P2, if inherit_dependencies then A depends on P1 and P2
    # if not inherit depenedencies, then A depends only on P and
    # may run before P1 and p2
    # requires using sctrl to modify running jobs
    inherit_dependencies: bool = True
