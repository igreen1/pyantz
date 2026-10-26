"""Submit jobs to a slurm HPC grid.

Each job is saved as JSON in the shared working directory and submitted with
``sbatch``, with slurm dependencies matching the pipeline's. On the compute node,
this module is run as a script (see :data:`ENTRY_MODULE_NAME`) to load and run
the job; jobs it submits are sbatched from there.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import re
import subprocess
import sys
import uuid
from graphlib import TopologicalSorter
from pathlib import Path
from typing import TYPE_CHECKING

from pyantz.infrastructure.config import (
    InitialConfig,
    JobConfig,
    JobWithContext,
    SubmissionFnType,
)
from pyantz.infrastructure.config.runners.slurm_runner import SlurmRunnerConfig
from pyantz.infrastructure.runner.job_manager import run_job

if TYPE_CHECKING:
    from collections.abc import Callable

ENTRY_BASH_FILE_PATH = Path(__file__).parent / "run.sh"
"""Script which sbatch runs; it runs the command it is given."""

# (not `__name__`, which is `__main__` when this module is run as a script)
ENTRY_MODULE_NAME = "pyantz.infrastructure.runner.slurm.slurm_runner"
"""Module run (``python -m``) on the compute node to run a job."""

CONFIG_FILE_ENVIRON_VAR_NAME: str = "PYANTZ_SLURM_CONFIG_FILE"
"""Environment variable holding the path of a *file* (the saved slurm runner
config), not a directory. It is only passed on to jobs through the environment
(``--export=ALL``), so prefer passing the path explicitly where possible."""

SECONDS_PER_MINUTE = 60
"""Used to convert the job time limit into sbatch's minutes."""


def start(config: InitialConfig) -> None:
    """Start the slurm pipeline up.

    The jobs are submitted in dependency order and this returns; they run (and
    submit their jobs) on the grid afterwards.

    Args:
        config: the validated configuration, with a ``slurm_sbatch`` submitter.

    Returns:
        None.

    Raises:
        TypeError: if the submitter of the configuration is not a slurm runner
        NotADirectoryError: if the slurm working directory does not exist
        subprocess.CalledProcessError: if ``sbatch`` fails.

    """
    logger = logging.getLogger(__name__)
    logger.debug("Starting slurm with config %s", config)

    runner_config = config.submitter
    if not isinstance(runner_config, SlurmRunnerConfig):
        msg = f"Expected a slurm_sbatch submitter, not {runner_config.type_!r}"
        raise TypeError(msg)

    working_dir = runner_config.working_dir
    if not working_dir.is_dir():
        msg = f"Slurm working_dir {working_dir} is not an existing directory"
        raise NotADirectoryError(msg)

    # store our global configuration in an environment variable
    slurm_config_path = _save_slurm_config(runner_config)
    _initial_submit(config, runner_config, slurm_config_path)


def _initial_submit(
    config: InitialConfig,
    runner_config: SlurmRunnerConfig,
    slurm_config_path: Path,
) -> None:
    """Submit our initial set of jobs.

    Done differently because rather than depending on current, the initial jobs
    have their own dependency graph that we must resolve up front.

    Args:
        config: the validated configuration; its variables are given to the jobs.
        runner_config: the slurm runner's configuration.
        slurm_config_path: the saved slurm runner configuration.

    Returns:
        None.

    Raises:
        subprocess.CalledProcessError: if ``sbatch`` fails.
        OSError: if a job can't be saved in the working directory.

    """
    dependency_adj_graph: dict[str, set[str]] = {
        str(job.job_id): {str(dep) for dep in (job.depends_on or set())}
        for job in config.jobs
    }
    submit_order = TopologicalSorter(graph=dependency_adj_graph).static_order()

    # directly call sbatch instead of submitter
    # because our parent node may not be a slurm job
    # so we don't want to make the child depend on the current
    sbatch = _create_sbatch(runner_config, slurm_config_path)

    def _submit(job: JobConfig, job_to_slurm_id_map: dict[str, str]) -> str:
        """Resolve context, compute dependencies, and call sbatch for one job.

        Args:
            job: the job to submit.
            job_to_slurm_id_map: pyantz job ids of the jobs submitted so far,
                mapped to their slurm job ids.

        Returns:
            str: the slurm job id of the submitted job.

        Raises:
            KeyError: if a dependency hasn't been submitted yet.
            subprocess.CalledProcessError: if ``sbatch`` fails.

        """
        with_context: JobWithContext = JobWithContext.from_config(job)
        with_context = with_context.model_copy(
            update={
                "variables": {
                    **(config.variables or {}),
                    **(with_context.variables or {}),
                }
            }
        )

        depends = None
        if with_context.depends_on:
            depends = [job_to_slurm_id_map[str(dep)] for dep in with_context.depends_on]

        return sbatch(with_context, depends)

    # start our jobs off!
    job_to_slurm_id_map: dict[str, str] = {}
    # job ids may one day be UUID objects
    # so this allows us to maintain them as "strings" even if job objects move to uuids
    job_lookup: dict[str, JobConfig] = {str(job.job_id): job for job in config.jobs}
    for job_id_s in submit_order:
        job = job_lookup[job_id_s]
        job_to_slurm_id_map[job_id_s] = _submit(job, job_to_slurm_id_map)


def _save_slurm_config(runner_config: SlurmRunnerConfig) -> Path:
    """Save the slurm configuration in a global location and store in environment.

    The configuration is saved in the working directory under a unique name, and
    its path put in :data:`CONFIG_FILE_ENVIRON_VAR_NAME`.

    Args:
        runner_config: the slurm runner's configuration.

    Returns:
        Path: where the slurm configuration was saved

    Raises:
        OSError: if the file can't be written.

    Example:
        .. testsetup:: slurm-save-config

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: slurm-save-config

            import os
            from pathlib import Path

            from pyantz.infrastructure.config.runners import SlurmRunnerConfig
            from pyantz.infrastructure.runner.slurm.slurm_runner import (
                _save_slurm_config,
            )

            path = _save_slurm_config(SlurmRunnerConfig(working_dir="."))
            print(path.name.startswith("global_slurm_config_"))
            print(os.environ["PYANTZ_SLURM_CONFIG_FILE"] == os.fspath(path))

        .. testoutput:: slurm-save-config

            True
            True

        .. testcleanup:: slurm-save-config

            del os.environ["PYANTZ_SLURM_CONFIG_FILE"]
            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    uid = str(uuid.uuid4())  # to reduce collisions if a user reuses a working_dir
    save_path = runner_config.working_dir / f"global_slurm_config_{uid!s}.json"
    save_path.write_text(runner_config.model_dump_json())
    os.environ[CONFIG_FILE_ENVIRON_VAR_NAME] = os.fspath(save_path)
    return save_path


def _create_job_submitter(
    config: SlurmRunnerConfig,
    slurm_config_path: Path,
) -> SubmissionFnType:
    """Create a method to accept a job config and submit it.

    Must be called within a slurm job. With ``inherit_dependencies``, the jobs
    waiting for the current job are made to wait for each submitted job too.

    Args:
        config: the slurm runner's configuration.
        slurm_config_path: the saved slurm runner configuration.

    Returns:
        SubmissionFnType: function which sbatches a job.

    Raises:
        RuntimeError: if ``SLURM_JOB_ID`` isn't set (not within a slurm job).
        subprocess.CalledProcessError: if ``squeue`` fails.

    """
    slurm_vars = _get_slurm_env_variables()
    curr_job_id = slurm_vars["job_id"]
    if curr_job_id is None:
        msg = "SLURM_JOB_ID is not set: jobs can only be submitted from within slurm"
        raise RuntimeError(msg)

    job_dependencies = _get_dependent_jobs(curr_job_id=curr_job_id)

    sbatch = _create_sbatch(config, slurm_config_path)

    def submit_fn(job: JobConfig) -> None:
        """Submit a new job to slurm, inheriting dependencies from the current node.

        Args:
            job: the job to submit.

        Returns:
            None.

        Raises:
            subprocess.CalledProcessError: if ``sbatch`` or ``scontrol`` fails.

        """
        # submit our job
        new_job_id = sbatch(job, None)
        if config.inherit_dependencies:
            _add_dependency(new_job_id, job_deps_to_update=job_dependencies)
            # `scontrol update Dependency=` replaces the whole list, so the next
            # child must be added to a list which includes this one
            for dependent, deps in job_dependencies.items():
                job_dependencies[dependent] = [*deps, new_job_id]

    return submit_fn


def _add_dependency(new_job_id: str, job_deps_to_update: dict[str, list[str]]) -> None:
    """Add new job id as a dep to the job deps listed.

    Args:
        new_job_id: slurm job id of the newly submitted job.
        job_deps_to_update: slurm job ids of the jobs to make wait for it, mapped
            to the ids they already wait for.

    Returns:
        None.

    Raises:
        subprocess.CalledProcessError: if ``scontrol`` fails.

    """

    def _create_sctrl(parent_job: str, prev_child_jobs: list[str]) -> list[str]:
        """Build an scontrol command that adds *new_job_id* to the dependency list.

        Args:
            parent_job: slurm job id of the job whose dependencies to update.
            prev_child_jobs: the slurm job ids it already waits for.

        Returns:
            list[str]: the ``scontrol update`` command.

        Raises:
            None.

        """
        # maybe todo: for now, we assume all deps are `afterok`... maybe we want others
        deps = ",".join([f"afterok:{i}" for i in (*prev_child_jobs, new_job_id)])
        return ["scontrol", "update", f"JobId={parent_job}", f"Dependency={deps}"]

    sctl_cmds = [
        _create_sctrl(parent, deps) for parent, deps in job_deps_to_update.items()
    ]

    _results = [subprocess.run(cmd, check=True) for cmd in sctl_cmds]  # noqa: S603


def _add_dependency_to_sbatch(
    args: list[str],
    dependencies: list[str],
    dependency_type: str = "afterok",
) -> list[str]:
    """Add the listed dependencies to the job submission.

    Any dependency the user gave (``--dependency=X``, ``--dependency X``, ``-d X`` or
    ``-dX``) is merged with the new ones into a single
    ``--dependency=X,afterok:..`` (or the job's dependency type) argument added at
    the end. The other arguments are left as they were.

    Args:
        args: the sbatch arguments.
        dependencies: slurm job ids the job must wait for.
        dependency_type: how to wait for them, e.g., ``afterok``.

    Returns:
        list[str]: the arguments with the combined ``--dependency``.

    Raises:
        ValueError: if a dependency flag has no value, or the user's dependency
            uses ``?`` (OR), which can't be combined.

    Example:
        .. testcode::

            from pyantz.infrastructure.runner.slurm.slurm_runner import (
                _add_dependency_to_sbatch,
            )

            args = ["--partition", "short", "-d", "afterany:7"]
            print(_add_dependency_to_sbatch(args, ["10", "11"]))

        .. testoutput::

            ['--partition', 'short', '--dependency=afterany:7,afterok:10,afterok:11']

    """
    remaining: list[str] = []
    former_deps: str | None = None
    arg_iter = iter(args)
    for arg in arg_iter:
        if arg in {"--dependency", "-d"}:
            former_deps = next(arg_iter, None)
            if former_deps is None:
                msg = f"{arg} was given without a value"
                raise ValueError(msg)
        elif arg.startswith("--dependency="):
            former_deps = arg.removeprefix("--dependency=")
        elif arg.startswith("-d") and not arg.startswith("--"):
            former_deps = arg.removeprefix("-d")
        else:
            remaining.append(arg)

    if former_deps is not None and "?" in former_deps:
        msg = (
            f"Cannot combine the dependency {former_deps!r} (it uses '?' for OR) "
            "with the dependencies on other pyantz jobs"
        )
        raise ValueError(msg)

    new_deps = ",".join([f"{dependency_type}:{i}" for i in dependencies])
    combined_deps = f"{former_deps},{new_deps}" if former_deps else new_deps

    return [*remaining, f"--dependency={combined_deps}"]


def _has_time_limit(slurm_args: list[str]) -> bool:
    """Check whether the sbatch arguments already set a time limit.

    Args:
        slurm_args: the sbatch arguments.

    Returns:
        bool: True if they include ``--time`` or ``-t`` in any form.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.infrastructure.runner.slurm.slurm_runner import _has_time_limit

            print(_has_time_limit(["-t10"]), _has_time_limit(["--test-only"]))

        .. testoutput::

            True False

    """
    return any(
        arg in {"--time", "-t"}
        or arg.startswith("--time=")
        or (arg.startswith("-t") and not arg.startswith("--"))
        for arg in slurm_args
    )


def _create_sbatch(
    config: SlurmRunnerConfig,
    slurm_config_path: Path,
) -> Callable[[JobConfig, list[str] | None], str]:
    """Sbatch the provided job config and return its new job id.

    Args:
        config: the slurm runner's configuration.
        slurm_config_path: the saved slurm runner configuration.

    Returns:
        Callable[[JobConfig, list[str] | None], str]: function which sbatches a
        job, waiting for the given slurm job ids, and returns its slurm job id.

    Raises:
        None.

    """

    def sbatch(
        job: JobConfig,
        dependencies: list[str] | None = None,
    ) -> str:
        """Serialise the job config, call sbatch, and return the new SLURM job id.

        Within a slurm job, the new job also waits for the current one. Unless
        the configured arguments say otherwise, the job gets a time limit of
        ``max_job_time_seconds`` and ``--kill-on-invalid-dep=yes``.

        Args:
            job: the job to submit.
            dependencies: slurm job ids the job must wait for, if any.

        Returns:
            str: the slurm job id of the submitted job.

        Raises:
            OSError: if the job can't be saved in the working directory.
            subprocess.CalledProcessError: if ``sbatch`` fails.
            ValueError: if the configured dependency arguments are invalid.

        """
        # save our config to a common location
        unique_job_file_name = str(uuid.uuid4()) + ".json"
        file_path = config.working_dir / unique_job_file_name

        file_path.write_text(job.model_dump_json(), encoding="utf-8")

        # keep the arguments as given: flags and their values must stay together
        slurm_args: list[str] = [*config.slurm_args]
        if "--parsable" not in slurm_args:
            slurm_args.append("--parsable")
        curr_job_id = _get_slurm_env_variables()["job_id"]
        if curr_job_id is not None:
            # may be sbatching from a local terminal so no guarantee curr job id exists
            # but if it is, our child should always wait for this parent to exit
            # this avoids race conditions when adding dependencies and aligns with
            # our idea of children as dependents for all pyantz jobs
            if dependencies is not None:
                dependencies = list({*dependencies, curr_job_id})
            else:
                dependencies = [curr_job_id]

        if dependencies is not None:
            slurm_args = _add_dependency_to_sbatch(
                slurm_args,
                dependencies,
                job.dependency_type,
            )

        # limit how long slurm lets the job run, unless the user chose a limit
        if not _has_time_limit(slurm_args):
            minutes = math.ceil(config.max_job_time_seconds / SECONDS_PER_MINUTE)
            slurm_args.append(f"--time={minutes}")

        # if a dependency fails, cancel the dependents rather than leaving them
        # pending forever; this matches how the local runner fails them
        if not any(arg.startswith("--kill-on-invalid-dep") for arg in slurm_args):
            slurm_args.append("--kill-on-invalid-dep=yes")

        # now, we have the file path to be run
        cmd: list[str] = [
            "sbatch",
            *slurm_args,
            os.fspath(ENTRY_BASH_FILE_PATH),
            sys.executable,
            "-m",
            ENTRY_MODULE_NAME,  # this module is the main entry point of the job!
            "-i",
            os.fspath(slurm_config_path),
            "-c",
            os.fspath(file_path),
        ]
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            check=True,
        )
        return result.stdout.decode().strip()

    return sbatch


def _get_dependent_jobs(curr_job_id: str) -> dict[str, list[str]]:
    """Get slurm job ids of jobs which depend on the job in which this is run.

    Args:
        curr_job_id: the slurm job id of the current job.

    Returns:
        dict[str, list[str]]: pending jobs which wait on *curr_job_id*, mapped to
            the ids of all the jobs they wait on (including *curr_job_id*)

    Raises:
        subprocess.CalledProcessError: if ``squeue`` fails.

    """
    logger = logging.getLogger(__name__)

    cmd = [
        "squeue",
        "--me",  # simplify output by looking only at current user
        "-h",  # no header
        "-t",
        "PD",  # only look at pending jobs
        "-o",
        "%i|%E",  # job_id|dependencies
    ]
    logger.debug("Running command: %s", cmd)
    result = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        check=True,
    )
    logger.debug("Resultant stderr: %s", result.stderr)
    logger.debug("Resultant stdout: %s", result.stdout)

    dependent_jobs: dict[str, list[str]] = {}
    for line in result.stdout.decode().splitlines():
        job_id, separator, dependency = line.strip().partition("|")
        if not separator:
            continue
        # dependencies look like `afterok:100(unfulfilled),afterok:101` or `(null)`
        dependency_ids = re.findall(r"\d+(?:_\d+)?", dependency)
        if curr_job_id in dependency_ids:
            dependent_jobs[job_id.strip()] = dependency_ids

    return dependent_jobs


def _get_slurm_env_variables() -> dict[str, str | None]:
    """Get slurm environment variables.

    Args:
        None.

    Returns:
        dict[str, str | None]: the job's id, name, nodes, number of tasks and
        cpus per task, each None if not set (e.g., outside of slurm).

    Raises:
        None.

    Example:
        .. testcode::

            import os

            from pyantz.infrastructure.runner.slurm.slurm_runner import (
                _get_slurm_env_variables,
            )

            os.environ["SLURM_JOB_ID"] = "1234"
            try:
                print(_get_slurm_env_variables()["job_id"])
            finally:
                del os.environ["SLURM_JOB_ID"]

        .. testoutput::

            1234

    """
    return {
        "job_id": os.environ.get("SLURM_JOB_ID"),
        "job_name": os.environ.get("SLURM_JOB_NAME"),
        "nodes": os.environ.get("SLURM_JOB_NODELIST"),
        "tasks": os.environ.get("SLURM_NTASKS"),
        "cpus": os.environ.get("SLURM_CPUS_PER_TASK"),
    }


def _load_job_config() -> tuple[JobWithContext, SlurmRunnerConfig, Path]:
    """Load our job config from shared storage using sys args.

    Reads ``-i``/``--slurm_config`` (path of the saved slurm runner
    configuration) and ``-c``/``--job_config`` (path of the job, relative to the
    working directory) from the command line.

    Args:
        None.

    Returns:
        tuple[JobWithContext, SlurmRunnerConfig, Path]: the job, the slurm runner
        configuration and the path of the saved configuration.

    Raises:
        ValueError: if either file doesn't exist.
        SystemExit: if the command line arguments are invalid.
        pydantic.ValidationError: if a file's contents are invalid.

    """
    logger = logging.getLogger(__name__)

    # for debugging purposes
    job_environment_variables = _get_slurm_env_variables()
    logger.debug("Starting up slurm grid job: %s", job_environment_variables)

    # find our configuration to be used by this job
    # paths are passed relative to the working directory
    parser = argparse.ArgumentParser(
        prog="Pyantz Slurm Child Job",
        description="Performs one of the jobs from pyantz.",
        epilog="Contact PyAntz authors for help!",
    )
    parser.add_argument(
        "-i",
        "--slurm_config",
        required=True,
        help="Path, absolute, to a JSON describing the slurm runner configuration.",
    )
    parser.add_argument(
        "-c",
        "--job_config",
        required=True,
        help="Path of the config to be used for this job; either absolute or"
        " relative to the working directory of this pyantz submission."
        " Must be valid JSON for a **JobWithContext**",
    )

    args = parser.parse_args()
    logger.debug("Received args: %s", args)

    config_file_arg: str = args.job_config
    slurm_config_arg: str = args.slurm_config
    slurm_config_path = Path(slurm_config_arg)
    if not slurm_config_path.exists():
        msg = f"No such slurm runner config file: {slurm_config_path}"
        logger.error(msg)
        raise ValueError(msg)

    slurm_config = SlurmRunnerConfig.model_validate_json(
        slurm_config_path.read_text(
            encoding="utf-8",
        ),
    )
    config_file_path = slurm_config.working_dir / config_file_arg
    if not config_file_path.exists():
        msg = f"No such job config file: {config_file_path}"
        logger.error(msg)
        raise ValueError(msg)

    job_config = JobWithContext.model_validate_json(
        config_file_path.read_text(
            encoding="utf-8",
        ),
    )
    return job_config, slurm_config, slurm_config_path


def _run_on_node() -> bool:
    """Run the job on this node.

    Args:
        None.

    Returns:
        bool: True if the job succeeded

    Raises:
        ValueError: if the job or configuration file doesn't exist.
        RuntimeError: if not run within a slurm job.

    """
    job_config, slurm_config, slurm_config_path = _load_job_config()

    submit_fn = _create_job_submitter(slurm_config, slurm_config_path)

    def wrapped_submitter(
        job_to_submit: JobConfig,
        # don't need parent id because the "parent id" is the slurm job id
        # which we grab from the current environment
        _parent_id: str | uuid.UUID | None = None,
    ) -> None:
        """Adapter that ignores the parent_id, using the SLURM env var instead.

        Args:
            job_to_submit: the job to submit.
            _parent_id: the id of the submitting job (ignored).

        Returns:
            None.

        Raises:
            subprocess.CalledProcessError: if ``sbatch`` or ``scontrol`` fails.

        """
        submit_fn(job_to_submit)

    return run_job(job_config=job_config, submitter_fn=wrapped_submitter)


if __name__ == "__main__":
    # running a child job!!! neat
    # a non-zero exit makes `afterok` dependents of a failed job never run
    sys.exit(0 if _run_on_node() else 1)
