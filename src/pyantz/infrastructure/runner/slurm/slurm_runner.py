"""Submit jobs to a slurm HPC grid."""

import argparse
import io
import logging
import os
import subprocess
import uuid
from graphlib import TopologicalSorter
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

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
CONFIG_FILE_ENVIRON_VAR_NAME: str = "PYANTZ_SLURM_CONFIG_DIR"


def start(config: InitialConfig[SlurmRunnerConfig]) -> None:
    """Start the slurm pipeline up."""
    logger = logging.getLogger(__name__)
    logger.debug("Starting slurm with config %s", config)

    # store our global configuration in an environment variable
    _save_slurm_config(config)
    _initial_submit(config)


def _initial_submit(config: InitialConfig[SlurmRunnerConfig]) -> None:
    """Submit our initial set of jobs.

    Done differently because rather than depending on current, the initial jobs
    have their own dependency graph that we must resolve up front.
    """
    dependency_adj_graph: dict[str, set[str]] = {
        str(job.job_id): {str(dep) for dep in (job.depends_on or set())}
        for job in config.jobs
    }
    submit_order = TopologicalSorter(graph=dependency_adj_graph).static_order()

    # directly call sbatch instead of submitter
    # because our parent node may not be a slurm job
    # so we don't want to make the child depend on the current
    sbatch = _create_sbatch(config.submitter)

    def _submit(job: JobConfig, job_to_slurm_id_map: dict[str, str]) -> str:
        """Wrap a job in the parent context and return its slurm id."""
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


def _save_slurm_config(config: InitialConfig[SlurmRunnerConfig]) -> None:
    """Save the slurm configuration in a global location and store in environment."""
    uid = str(uuid.uuid4())  # to reduce collisions if a user re-uses a working_dir
    save_path = config.submitter.working_dir / f"global_slurm_config_{uid!s}.json"
    save_path.write_text(config.submitter.model_dump_json())
    os.environ[CONFIG_FILE_ENVIRON_VAR_NAME] = os.fspath(save_path)


def _load_slurm_config() -> SlurmRunnerConfig:
    """Load our slurm runner configuration from the global json."""
    save_path = os.environ.get(CONFIG_FILE_ENVIRON_VAR_NAME)
    if not save_path:
        raise RuntimeError
    config_file = Path(save_path)
    return SlurmRunnerConfig.model_validate_json(
        config_file.read_text(encoding="utf-8")
    )


def _create_job_submitter(config: SlurmRunnerConfig) -> SubmissionFnType:
    """Create a method to accept a job config and submit it."""
    slurm_vars = _get_slurm_env_variables()
    curr_job_id = slurm_vars["job_id"]
    if curr_job_id is None:
        raise RuntimeError

    job_dependencies = _get_dependent_jobs(curr_job_id=curr_job_id)

    sbatch = _create_sbatch(config)

    def submit_fn(job: JobConfig) -> None:
        """Submit the job to the grid."""
        # submit our job
        new_job_id = sbatch(job, None)
        if config.inherit_dependencies:
            _add_dependency(new_job_id, job_deps_to_update=job_dependencies)

    return submit_fn


def _add_dependency(new_job_id: str, job_deps_to_update: dict[str, list[str]]) -> None:
    """Add new job id as a dep to the job deps listed."""

    def _create_sctrl(parent_job: str, prev_child_jobs: list[str]) -> list[str]:
        # maybe todo: for now, we assume all deps are `afterok`... maybe we want others
        deps = ",".join([f"afterok:{i}" for i in (*prev_child_jobs, new_job_id)])
        return ["scontrol", "update", f"JobId={parent_job}", f"Dependency={deps}"]

    sctl_cmds = [
        _create_sctrl(parent, deps) for parent, deps in job_deps_to_update.items()
    ]

    _results = [subprocess.run(cmd, check=True) for cmd in sctl_cmds]  # noqa: S603


def _add_dependency_to_sbatch(args: list[str], dependencies: list[str]) -> list[str]:
    """Add the listed dependencies to the job submission."""
    dep_arg_idx = -1
    for i, arg in enumerate(args):
        if "--dependency" in arg:
            dep_arg_idx = i

    former_deps: str | None
    # if dependency and the list are in two consecutive arguments
    if dep_arg_idx != -1 and args[dep_arg_idx] == "--dependency":
        if len(args) - 1 == dep_arg_idx:
            raise ValueError  # last element is just a danling --dependency??
        former_deps = args.pop(dep_arg_idx) + args.pop(dep_arg_idx)
    elif dep_arg_idx != -1:
        former_deps = args.pop(dep_arg_idx)
    else:
        former_deps = None

    new_deps = ",".join([f"afterok:{i}" for i in dependencies])

    combined_deps = (
        former_deps + "," + new_deps if former_deps else f"--dependency={new_deps}"
    )

    return [*args, combined_deps]


def _create_sbatch(
    config: SlurmRunnerConfig,
) -> Callable[[JobConfig, list[str] | None], str]:
    """Sbatch the provided job config and return its new job id."""

    def sbatch(
        job: JobConfig,
        dependencies: list[str] | None = None,
    ) -> str:
        # save our config to a common location
        unique_job_file_name = str(uuid.uuid4()) + ".json"
        file_path = config.working_dir / unique_job_file_name

        file_path.write_text(job.model_dump_json(), encoding="utf-8")

        slurm_args: list[str] = list({*config.slurm_args, "--parsable"})
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
            slurm_args = _add_dependency_to_sbatch(slurm_args, dependencies)

        # now, we have the file path to be run
        cmd: list[str] = [
            "sbatch",
            *slurm_args,
            os.fspath(ENTRY_BASH_FILE_PATH),
            os.fspath(__file__),  # this job is the main entry point!
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
    """Get slurm job ids of jobs which depend on the job in which this is run."""
    logger = logging.getLogger(__name__)

    cmd = [
        "squeue",
        "--me",  # simplify output by looking only at current user
        "-t PD",  # only look at pending jobs
        '--format="%i %E"',  # job_id,depends
    ]
    logger.debug("Running command: %s", cmd)
    result = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        check=True,
    )
    logger.debug("Resultant stderr: %s", result.stderr)
    logger.debug("Resultant stdout: %s", result.stdout)

    stdout = io.StringIO(result.stdout.decode())
    job_results = pl.read_csv(stdout, separator=" ")
    dep_jobs = (
        job_results.with_columns(  # pyright: ignore[reportUnknownMemberType]
            pl.col("DEPENDENCY").str.extract_all(r"\d+").alias("deps"),
        )
        .filter(
            pl.col("deps").list.contains(curr_job_id),  # pyright: ignore[reportUnknownMemberType]
        )
        .to_dicts()
    )

    return {entry["JOBID"]: entry["deps"] for entry in dep_jobs}


def _get_slurm_env_variables() -> dict[str, str | None]:
    """Get slurm environment variables."""
    return {
        "job_id": os.environ.get("SLURM_JOB_ID"),
        "job_name": os.environ.get("SLURM_JOB_NAME"),
        "nodes": os.environ.get("SLURM_JOB_NODELIST"),
        "tasks": os.environ.get("SLURM_NTASKS"),
        "cpus": os.environ.get("SLURM_CPUS_PER_TASK"),
    }


def _load_job_config() -> JobWithContext:
    """Load our job config from shared storage using sys args."""
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
        help="Path, relative to the working directory of this pyantz submission,"
        " of the config to be used for this job."
        " Must be valid JSON for a **JobWithContext**",
    )

    args = parser.parse_args()
    logger.debug("Received args: %s", args)

    config_file_arg: str = args.job_config
    slurm_config_arg: str = args.slurm_config
    slurm_config_path = Path(slurm_config_arg)
    if not slurm_config_path.exists():
        logger.error("No such directory: %s", slurm_config_path)
        raise ValueError

    slurm_config = SlurmRunnerConfig.model_validate_json(
        slurm_config_path.read_text(
            encoding="utf-8",
        ),
    )
    config_file_path = slurm_config.working_dir / config_file_arg
    if not config_file_path.exists():
        logger.error("No such job config: %s", config_file_path)
        raise ValueError

    return JobWithContext.model_validate_json(
        config_file_path.read_text(
            encoding="utf-8",
        ),
    )


def _run_on_node() -> None:
    """Run the job on this node."""
    job_config = _load_job_config()
    slurm_config = _load_slurm_config()

    submit_fn = _create_job_submitter(slurm_config)

    def wrapped_submitter(
        job_to_submit: JobConfig,
        # don't need parent id beacuse the "parent id" is the slurm job id
        # which we grab from the current environment
        _parent_id: str | uuid.UUID | None = None,
    ) -> None:
        submit_fn(job_to_submit)

    run_job(job_config=job_config, submitter_fn=wrapped_submitter)


if __name__ == "__main__":
    # running a child job!!! neat
    _run_on_node()
