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

Something like the below is possible, which fits many use cases::

                  C1
                /
    A -> B -> C
                \ C2

Example of :class:`SlurmRunnerConfig`:

    .. testcode::

        from pyantz.infrastructure.config.runners import SlurmRunnerConfig

        config = SlurmRunnerConfig(
            working_dir="/shared/pipeline", slurm_args=["--partition=short"]
        )
        print(config.type_, config.max_job_time_seconds, config.slurm_args)

    .. testoutput::

        slurm_sbatch 10000 ['--partition=short']
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_JOB_TIMEOUT: int = 10_000  # about 2.8 hours
"""Default of :attr:`SlurmRunnerConfig.max_job_time_seconds`."""


class SlurmRunnerConfig(BaseModel):
    """Configuration used by the slurm submitters."""

    model_config = ConfigDict(frozen=True)

    type_: Literal["slurm_sbatch"] = "slurm_sbatch"
    """Identifies this submitter configuration."""

    max_job_time_seconds: int = DEFAULT_JOB_TIMEOUT
    """Max time a job can be running before slurm stops it. Passed to sbatch as
    ``--time`` (in whole minutes, rounded up) unless ``slurm_args`` sets a time
    limit."""

    slurm_args: list[str] = Field(default_factory=list)
    """Extra arguments for every sbatch call. Unless they include
    ``--kill-on-invalid-dep``, jobs are submitted with
    ``--kill-on-invalid-dep=yes`` so that when a job fails, the jobs waiting on
    it are cancelled instead of staying pending forever."""

    working_dir: Path
    """Directory shared between the submitting node and the compute nodes. Not
    checked when the config is parsed: with a remote host it only exists there
    (it is checked when the slurm runner starts)."""

    inherit_dependencies: bool = True
    """If some job A depends on job P and job P submits jobs P1 and P2: if true,
    A depends on P1 and P2 too (which needs ``scontrol`` to modify the pending
    jobs); if false, A depends only on P and may run before P1 and P2."""
