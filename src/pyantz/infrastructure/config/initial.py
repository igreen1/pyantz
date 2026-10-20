"""Top-level pipeline configuration.

:class:`InitialConfig` is the root object that a user creates (in JSON or
Python) to describe a complete pipeline run.  It ties together the job list,
the submitter (local or SLURM), optional global variables, and the host
on which the submitter should be started.
"""

from collections.abc import Mapping
from typing import Annotated, Any, Self

from pydantic import BaseModel, BeforeValidator, Field, model_validator

from pyantz.infrastructure.virtual import compile_virtual

from .graph_validation import find_graph_problems
from .host_config import HostConfig, LocalConfig
from .job import JobConfig, make_job
from .runners import LocalRunnerConfig, SlurmRunnerConfig

type AnyRunner = LocalRunnerConfig | SlurmRunnerConfig


def make_and_compile(jobs: Any) -> list[JobConfig]:  # noqa: ANN401
    """Validate raw job dicts and compile virtual jobs into concrete ones.

    Used as the ``BeforeValidator`` for :attr:`InitialConfig.jobs`. First calls
    :func:`~pyantz.infrastructure.config.job.make_job` on each element to
    produce typed job configs, then passes the result through
    :func:`~pyantz.infrastructure.virtual.compile.compile_virtual` to expand
    any virtual jobs.

    Args:
        jobs: An iterable of raw job-config dicts or pre-validated job config
            objects.

    Returns:
        Flat list of compiled :class:`~pyantz.infrastructure.config.job.JobConfig`
        instances with all virtual jobs expanded.

    """
    job_configs = list(map(make_job, jobs))
    problems = find_graph_problems(job_configs)
    if problems:
        msg = "Invalid jobs:\n- " + "\n- ".join(problems)
        raise ValueError(msg)
    return compile_virtual(job_configs)


class InitialConfig[S: (LocalRunnerConfig, SlurmRunnerConfig)](BaseModel):
    """Configuration of the overall system.

    Passed by the user and used to setup the system. This is the
    primary user configuration.
    """

    jobs: Annotated[tuple[JobConfig, ...], BeforeValidator(make_and_compile)]

    submitter: S = Field(discriminator="type_")

    variables: Mapping[str, Any] = Field(default_factory=dict)

    host: HostConfig = LocalConfig()

    @model_validator(mode="after")
    def _check_dependencies_exist(self) -> Self:
        """Ensure every job only depends on jobs in this configuration."""
        known_ids = {job.job_id for job in self.jobs}
        unknown = {
            job.job_id: sorted(job.depends_on - known_ids)
            for job in self.jobs
            if job.depends_on and job.depends_on - known_ids
        }
        if unknown:
            msg = f"Jobs depend on unknown job ids (job -> missing): {unknown}"
            raise ValueError(msg)
        return self

    def with_new_host(self, new_host: HostConfig) -> Self:
        """Return this configuration with a new host setup."""
        return self.model_copy(update={"host": new_host})
