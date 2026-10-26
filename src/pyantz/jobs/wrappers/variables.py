"""Wrap jobs in variable contexts.

A user may wish to declare some variables locally for a few common jobs.
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    WithJsonSchema,
    model_validator,
)

from pyantz.infrastructure.config import (
    JobConfig,
    JobPipeline,
    JobWithContext,
    add_parameters,
    import_module_item_by_name,
)
from pyantz.infrastructure.runner.job_manager import (
    JobVariables,
    run_job_no_parent_wrapper,
)

if TYPE_CHECKING:
    from pyantz.infrastructure.config import SubmissionFnType


class SetVariables(BaseModel):
    """Parameters for running a job which sets variables."""

    model_config = ConfigDict(frozen=True)

    setter_job: Annotated[
        Callable[..., Any],
        BeforeValidator(import_module_item_by_name),
        WithJsonSchema({"type": "string"}),
    ]
    """Import path of the function which sets the variables; it is called with
    ``set_var`` (a function taking a name and a value) and ``set_job_kwargs``."""

    set_job_kwargs: Mapping[str, Any]
    """Keyword arguments to pass to the setter job."""

    jobs: JobPipeline
    """Jobs to submit with the variables set by the setter job."""


@add_parameters(SetVariables)
def set_variables(params: SetVariables, submit_fn: SubmissionFnType) -> bool:
    """Set the variables for subsequent defined jobs.

    The `setter_job` is a slightly abnormal job. One of the parameters it accepts
    shall be `set_var`, which is a closure that will set the enclosing variables.
    Once it returns, ``jobs`` are submitted with the variables it set.

    Args:
        params: the job's parameters, validated as :class:`SetVariables`.
        submit_fn: function to submit ``jobs`` with.

    Parameters:
        setter_job (str): import path of the function which sets the variables by
            calling ``set_var(name, value)``.
        set_job_kwargs (Mapping[str, Any]): more keyword arguments for the setter
            job.
        jobs (JobPipeline): jobs to submit with the variables.

    Returns:
        bool: True once the jobs are submitted, False if the setter job raises
        (and nothing is submitted).

    Raises:
        None: failures of the setter job are logged and reported by returning
            False.

    Example:
        .. testcode::

            from pyantz.jobs.wrappers.variables import set_variables

            # in a configuration, the setter job is given by its import path
            def find_latest(set_var, prefix):
                set_var("latest", f"{prefix}_042")

            submitted = []
            set_variables(
                {
                    "setter_job": find_latest,
                    "set_job_kwargs": {"prefix": "run"},
                    "jobs": [
                        {
                            "function": "pyantz.jobs.testing.nop.do_nothing",
                            "parameters": {"path": "%{latest}/out.txt"},
                        },
                    ],
                },
                submitted.append,
            )
            print(submitted[0].variables)

        .. testoutput::

            {'latest': 'run_042'}

    """
    logger = logging.getLogger(__name__)
    new_variables: dict[str, Any] = {}

    def set_var(key: str, value: Any) -> None:  # noqa: ANN401
        """Store *value* under *key* in the enclosing ``new_variables`` dict.

        Args:
            key: the name of the variable.
            value: the value of the variable.

        Returns:
            None.

        Raises:
            None.

        """
        nonlocal new_variables
        new_variables[key] = value

    try:
        params.setter_job(
            set_var=set_var,
            **params.set_job_kwargs,
        )
    except Exception as exc:
        logger.exception("Unknown error in external set variable job.", exc_info=exc)
        return False
    else:
        for job in params.jobs:
            updated_job = JobWithContext.from_config(job).inherit_context(new_variables)
            submit_fn(updated_job)
        return True


class VariableContextParams(BaseModel):
    """Parameters for submitting jobs with variables shared between them."""

    model_config = ConfigDict(frozen=True)

    jobs: JobPipeline
    """Jobs to submit with the new variables."""

    shared_variables: Mapping[str, Any]
    """Variables to add to the jobs when submitted."""


@add_parameters(VariableContextParams)
def run_jobs_in_context(
    params: VariableContextParams,
    submit_fn: SubmissionFnType,
) -> bool:
    """Submit the set of jobs with the shared variables. Not really anything fancy.

    When the jobs are submitted, they also inherit the variables of this job; the
    shared variables take precedence over those.

    Args:
        params: the job's parameters, validated as :class:`VariableContextParams`.
        submit_fn: function to submit the jobs with.

    Parameters:
        jobs (JobPipeline): jobs to submit.
        shared_variables (Mapping[str, Any]): variables to give every job.

    Returns:
        bool: True once the jobs are submitted.

    Raises:
        None.

    Example:
        .. testcode::

            from pyantz.jobs.wrappers.variables import run_jobs_in_context

            nop = "pyantz.jobs.testing.nop.do_nothing"
            submitted = []
            run_jobs_in_context(
                {
                    "shared_variables": {"dataset": "train", "seed": 1},
                    "jobs": [
                        {"function": nop, "parameters": {"step": "prepare"}},
                        {"function": nop, "parameters": {"step": "fit"}},
                    ],
                },
                submitted.append,
            )
            for job in submitted:
                print(job.parameters["step"], job.variables)

        .. testoutput::

            prepare {'dataset': 'train', 'seed': 1}
            fit {'dataset': 'train', 'seed': 1}

    """
    for job in params.jobs:
        # add context
        updated_job = JobWithContext.from_config(job).inherit_context(
            params.shared_variables
        )
        submit_fn(updated_job)

    return True


class TemporaryDirectoryParams(BaseModel):
    """Params for providing a set of jobs a temporary directory."""

    model_config = ConfigDict(frozen=True)

    jobs: JobPipeline
    """Jobs to run."""

    variable_name: str
    """Name of the variable holding the path to the temporary directory."""

    submit_type: Literal["local", "remote"] = "local"
    """If ``local``, the jobs run in this job, one after another; if ``remote``,
    they are submitted. With ``remote``, the user must provide a SHARED
    NON-TEMPORARY location in ``shared_working_dir`` in which to place the
    temporary directory, since it must outlive this job."""

    shared_working_dir: Path | None = None
    """Directory in which the temporary directory is made: required with
    ``remote``; with ``local``, by default the system's temporary location."""

    @model_validator(mode="after")
    def validate_submit_and_dir(self) -> TemporaryDirectoryParams:
        """Ensure that remote mode has a shared working directory.

        Args:
            None.

        Returns:
            TemporaryDirectoryParams: the validated parameters.

        Raises:
            ValueError: if ``submit_type`` is ``remote`` without a
                ``shared_working_dir``.

        """
        if self.submit_type == "remote" and self.shared_working_dir is None:
            msg = "shared_working_dir is required when submit_type is 'remote'"
            raise ValueError(msg)
        return self


@add_parameters(TemporaryDirectoryParams)
def run_jobs_with_temp_dir(
    params: TemporaryDirectoryParams, submit_fn: SubmissionFnType
) -> bool:
    """Run jobs with a temporary directory.

    The path of the directory is given to the jobs in the ``variable_name``
    variable. With ``submit_type`` ``local``, the jobs run in this job, one after
    another, stopping at the first failure, and the directory is deleted when they
    finish; they can't submit other jobs. With ``remote``, the jobs are submitted
    between a job which creates the directory and one which deletes it once they
    have all succeeded.

    Args:
        params: the job's parameters, validated as
            :class:`TemporaryDirectoryParams`.
        submit_fn: function to submit the jobs with (``remote`` only).

    Parameters:
        jobs (JobPipeline): jobs to run.
        variable_name (str): name of the variable holding the directory's path.
        submit_type (str): ``local`` or ``remote``. Defaults to ``local``.
        shared_working_dir (Path | None): directory to make the temporary
            directory in; required with ``remote``. Defaults to None.

    Returns:
        bool: with ``local``, True if every job succeeded, otherwise False; with
        ``remote``, True once the jobs are submitted.

    Raises:
        OSError: if the temporary directory can't be created (``local``).

    Example:
        .. testsetup:: wrappers-temp-dir

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: wrappers-temp-dir

            import os

            from pyantz.jobs.wrappers.variables import run_jobs_with_temp_dir

            success = run_jobs_with_temp_dir(
                {
                    "variable_name": "scratch",
                    "shared_working_dir": ".",
                    "jobs": [
                        {
                            "function": "pyantz.jobs.files.simple.create",
                            "parameters": {"path": "%{scratch}/temp.txt"},
                        },
                        {
                            "function": "pyantz.jobs.files.check.file_exists",
                            "parameters": {"file": "%{scratch}/temp.txt"},
                        },
                    ],
                },
                lambda job: None,
            )
            print(success, os.listdir())  # the directory is gone again

        .. testoutput:: wrappers-temp-dir

            True []

        .. testcleanup:: wrappers-temp-dir

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    if params.submit_type == "local":
        return _run_jobs_temp_dir_local(params)

    return _run_jobs_temp_dir_remote(params, submit_fn)


def _run_jobs_temp_dir_remote(
    params: TemporaryDirectoryParams, submit_fn: SubmissionFnType
) -> bool:
    """Submit the jobs to be run after creating a working dir for them.

    Submits a job creating a uniquely named directory in ``shared_working_dir``,
    the jobs (depending on it, with the directory in their variables) and a job
    deleting the directory, which depends on all of them.

    Args:
        params: the parameters of :func:`run_jobs_with_temp_dir`.
        submit_fn: function to submit the jobs with.

    Returns:
        bool: True once the jobs are submitted.

    Raises:
        ValueError: if ``shared_working_dir`` isn't set.

    Example:
        .. testcode::

            from pyantz.jobs.wrappers.variables import (
                TemporaryDirectoryParams,
                _run_jobs_temp_dir_remote,
            )

            nop = "pyantz.jobs.testing.nop.do_nothing"
            params = TemporaryDirectoryParams(
                jobs=[{"function": nop, "parameters": {}}],
                variable_name="scratch",
                submit_type="remote",
                shared_working_dir="/shared",
            )
            submitted = []
            _run_jobs_temp_dir_remote(params, submitted.append)
            print([job.name for job in submitted])

        .. testoutput::

            ['__autogenerate_mkdir__', None, '__autogenerated_clean_up_dir__']

    """
    if params.shared_working_dir is None:
        msg = "shared_working_dir is required when submit_type is 'remote'"
        raise ValueError(msg)
    dir_name = f"tempdir_{uuid.uuid4().hex}"
    dir_path = params.shared_working_dir / dir_name

    # create the working directory in a separate job
    mkdir_job = JobConfig(
        name="__autogenerate_mkdir__",
        function="pyantz.jobs.files.simple.mkdir",  # type: ignore[arg-type]
        parameters={"dir_path": dir_path},
    )

    # and we have to delete it
    delete_dir_job = JobConfig(
        name="__autogenerated_clean_up_dir__",
        # should only happen after everything else has completed!
        depends_on={job.job_id for job in (*params.jobs, mkdir_job)},
        function="pyantz.jobs.files.simple.delete",  # type: ignore[arg-type]
        # the jobs will have put files in it
        parameters={"path": dir_path, "recursive": True},
    )

    # mkdir must happen first so make everything depend on mkdir.
    # The jobs find the directory in the variable, which they inherit from this job.
    # Note the cleanup only runs if every job succeeded (a failure fails its dependents)
    contextual_jobs = [
        JobWithContext.from_config(
            job.model_copy(
                update={"depends_on": {*(job.depends_on or ()), mkdir_job.job_id}}
            ),
        ).inherit_context({params.variable_name: os.fspath(dir_path)})
        for job in params.jobs
    ]
    # notional order, but with the dependencies may not fully matter
    jobs = [mkdir_job, *contextual_jobs, delete_dir_job]

    for job in jobs:
        submit_fn(job)

    return True


def _run_jobs_temp_dir_local(params: TemporaryDirectoryParams) -> bool:
    """Run the jobs locally with a temporary directory.

    Args:
        params: the parameters of :func:`run_jobs_with_temp_dir`.

    Returns:
        bool: True if every job succeeded, False at the first which fails.

    Raises:
        OSError: if the temporary directory can't be created.

    """
    curr_variables: Final[Mapping[str, Any]] = (
        _vars if (_vars := JobVariables.get()) else {}
    )

    def _no_submit(_job: JobConfig) -> None:
        """Refuse submissions, which would run after the directory is deleted.

        Args:
            _job: the job which was to be submitted (ignored).

        Returns:
            None: never returns.

        Raises:
            RuntimeError: always.

        """
        msg = (
            "Jobs run by run_jobs_with_temp_dir in local mode cannot submit other "
            "jobs because the temporary directory is deleted when they finish; "
            "use submit_type 'remote' instead"
        )
        raise RuntimeError(msg)

    with tempfile.TemporaryDirectory(dir=params.shared_working_dir) as tmpdirname:
        variables_with_dir: Final[Mapping[str, Any]] = {
            **curr_variables,
            params.variable_name: tmpdirname,
        }
        success = True
        for job in params.jobs:
            job_with_parent_context = JobWithContext.from_config(job).inherit_context(
                variables_with_dir
            )
            if not run_job_no_parent_wrapper(job_with_parent_context, _no_submit):
                success = False
                break

    return success
