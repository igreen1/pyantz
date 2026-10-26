"""Top-level pipeline configuration.

:class:`InitialConfig` is the root object that a user creates (in JSON or
Python) to describe a complete pipeline run.  It ties together the job list,
the submitter (local or SLURM), optional global variables, and the host
on which the submitter should be started.

Example of :class:`InitialConfig`:

    .. testcode::

        from pyantz.infrastructure.config import InitialConfig

        config = InitialConfig.model_validate(
            {
                "jobs": [
                    {
                        "function": "pyantz.jobs.testing.nop.do_nothing",
                        "parameters": {},
                    },
                ],
                "submitter": {"type_": "local_proc", "working_directory": "."},
                "variables": {"data_dir": "/data"},
            }
        )
        print(config.host.type_, config.submitter.type_, len(config.jobs))

    .. testoutput::

        local local_proc 1
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Self

from pydantic import BaseModel, BeforeValidator, Field, model_validator

from pyantz.infrastructure.virtual import compile_virtual

from .graph_validation import find_graph_problems
from .host_config import HostConfig, LocalConfig
from .job import JobConfig, make_job
from .runners import LocalRunnerConfig, SlurmRunnerConfig

type AnyRunner = Annotated[
    LocalRunnerConfig | SlurmRunnerConfig, Field(discriminator="type_")
]
"""Any submitter configuration, told apart by its ``type_``."""


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

    Raises:
        ValueError: if the jobs have duplicate ids, unknown dependencies or a
            dependency cycle, or a job is invalid.
        TypeError: if a job isn't a mapping or job config.

    Example:
        .. testcode::

            from pyantz.infrastructure.config.initial import make_and_compile

            jobs = make_and_compile(
                [
                    {
                        "function": "pyantz.virtual.add_variables.AddVariables",
                        "parameters": {"variables": {"x": 1}},
                        "job_id": "vars",
                    },
                    {
                        "function": "pyantz.jobs.testing.nop.do_nothing",
                        "parameters": {},
                        "depends_on": ["vars"],
                    },
                ]
            )
            print([job.function.__name__ for job in jobs])

        .. testoutput::

            ['run_jobs_in_context']

    """
    job_configs = list(map(make_job, jobs))
    problems = find_graph_problems(job_configs)
    if problems:
        msg = "Invalid jobs:\n- " + "\n- ".join(problems)
        raise ValueError(msg)
    return compile_virtual(job_configs)


class InitialConfig(BaseModel):
    """Configuration of the overall system.

    Passed by the user and used to setup the system. This is the
    primary user configuration.
    """

    jobs: Annotated[tuple[JobConfig, ...], BeforeValidator(make_and_compile)]
    """The jobs to run, with virtual jobs compiled away."""

    submitter: AnyRunner
    """How the jobs are submitted: ``local_proc`` or ``slurm_sbatch``."""

    variables: Mapping[str, Any] = Field(default_factory=dict)
    """Variables available to every job."""

    host: HostConfig = LocalConfig()
    """Where the submitter runs: this machine, over ssh or in a container."""

    @model_validator(mode="after")
    def _check_dependencies_exist(self) -> Self:
        """Ensure every job only depends on jobs in this configuration.

        Args:
            None.

        Returns:
            Self: the validated configuration.

        Raises:
            ValueError: if a job depends on a job id which isn't in the
                configuration.

        """
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
        """Return this configuration with a new host setup.

        Args:
            new_host: the host configuration to use.

        Returns:
            Self: a copy of this configuration with ``host`` replaced.

        Raises:
            None.

        Example:
            .. testcode::

                from pyantz.infrastructure.config import InitialConfig, LocalConfig

                config = InitialConfig.model_validate(
                    {
                        "jobs": [],
                        "submitter": {"type_": "local_proc", "working_directory": "."},
                        "host": {"type_": "container", "name": "builder"},
                    }
                )
                print(config.with_new_host(LocalConfig()).host.type_)

            .. testoutput::

                local

        """
        return self.model_copy(update={"host": new_host})
