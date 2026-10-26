"""Configuration of a virtual job.

A virtual job only exists while a configuration is compiled: it is replaced by
the concrete jobs its parameters model compiles to, usually wrapping the jobs
which depend on it. See :mod:`pyantz.infrastructure.virtual`.

Example of :class:`VirtualJobConfig`:

    .. testcode::

        from pyantz.infrastructure.config import JobConfig, VirtualJobConfig

        virtual_job = VirtualJobConfig(
            function="pyantz.virtual.add_variables.AddVariables",
            parameters={"variables": {"x": 1}},
        )
        nop = "pyantz.jobs.testing.nop.do_nothing"
        job = JobConfig(function=nop, parameters={})
        (compiled,) = virtual_job.compile_virtual([job])
        print(compiled.function.__name__, compiled.parameters["shared_variables"])

    .. testoutput::

        run_jobs_in_context {'x': 1}
"""

from __future__ import annotations

from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Protocol,
    Self,
    runtime_checkable,
)

from pydantic import AfterValidator, BeforeValidator, ConfigDict

from pyantz.infrastructure.config.parameters import is_virtual

from .abstract_job import AbstractJobConfig
from .fn_utils import import_module_item_by_name

if TYPE_CHECKING:
    from collections.abc import Mapping

    from . import JobConfig


@runtime_checkable
class VirtualParamModel(Protocol):
    """Model to be inherited by parameters of virtual jobs.

    Virtual jobs have no functions, so they are purely defined by
    these parameter models, which will compile into a real set of
    job configs (which will primarily focus on the parameters).
    """

    @abstractmethod
    def compile_virtual(self, dependent_jobs: list[JobConfig]) -> list[JobConfig]:
        """Compile our job into a list of real jobs.

        Args:
            dependent_jobs: the (compiled) jobs which depend on the virtual job.

        Returns:
            list[JobConfig]: the concrete jobs replacing the virtual job and
            ``dependent_jobs``.

        Raises:
            Exception: implementations may raise if they can't compile.

        """

    @classmethod
    @abstractmethod
    def model_validate(cls, params: Mapping[str, Any]) -> Self:
        """Pydantic model validation.

        Args:
            params: the virtual job's parameters.

        Returns:
            Self: the validated parameters.

        Raises:
            pydantic.ValidationError: if the parameters are invalid.

        """


def _is_virtual(params: VirtualParamModel) -> VirtualParamModel:
    """Check that a virtual job's ``function`` is marked as virtual.

    Args:
        params: the parameters model given as the job's ``function``.

    Returns:
        VirtualParamModel: ``params`` unchanged.

    Raises:
        ValueError: if ``params`` isn't marked with
            :func:`~pyantz.infrastructure.config.mark_virtual`.

    """
    if not is_virtual(params):
        msg = (
            f"{params!r} is not a virtual job: "
            "its parameter model must be decorated with `mark_virtual`"
        )
        raise ValueError(msg)
    return params


class VirtualJobConfig(AbstractJobConfig):
    """A job which is only used to create an ordered set of 'real' jobs."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    """Human readable name."""

    function: Annotated[
        type[VirtualParamModel],
        AfterValidator(_is_virtual),
        BeforeValidator(import_module_item_by_name),
    ]
    """Import path of the virtual job's parameters model, which must be marked
    with :func:`~pyantz.infrastructure.config.mark_virtual`."""

    virtual: Literal[True] = True
    """Denotes that this is a virtual job."""

    @property
    def compiled_params(self) -> VirtualParamModel:
        """Build our parameters.

        Args:
            None.

        Returns:
            VirtualParamModel: the parameters, validated by ``function``.

        Raises:
            pydantic.ValidationError: if the parameters are invalid.

        """
        return self.function.model_validate(self.parameters)

    def compile_virtual(self, dependent_jobs: list[JobConfig]) -> list[JobConfig]:
        """Compile from our parameters to real jobs.

        Args:
            dependent_jobs: the (compiled) jobs which depend on this job.

        Returns:
            list[JobConfig]: the concrete jobs replacing this job and
            ``dependent_jobs``.

        Raises:
            pydantic.ValidationError: if the parameters are invalid.

        """
        return self.compiled_params.compile_virtual(dependent_jobs)
