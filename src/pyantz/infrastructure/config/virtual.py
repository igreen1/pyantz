"""Configuration of a virtual job."""

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

from .abtrast_job import AbstractJobConfig
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
        """Compile our job into a list of real jobs."""

    @classmethod
    @abstractmethod
    def model_validate(cls, params: Mapping[str, Any]) -> Self:
        """Pydantic model validation."""


def _is_virtual(params: VirtualParamModel) -> VirtualParamModel:
    if not is_virtual(params):
        raise ValueError
    return params


class VirtualJobConfig(AbstractJobConfig):
    """A job which is only used to create an ordered set of 'real' jobs."""

    model_config = ConfigDict(frozen=True)

    # human readable name
    name: str | None = None

    # points to the virtual job parameter model
    function: Annotated[
        type[VirtualParamModel],
        AfterValidator(_is_virtual),
        BeforeValidator(import_module_item_by_name),
    ]

    virtual: Literal[True] = True

    @property
    def compiled_params(self) -> VirtualParamModel:
        """Build our parameters."""
        return self.function.model_validate(self.parameters)

    def compile_virtual(self, dependent_jobs: list[JobConfig]) -> list[JobConfig]:
        """Compile from our parameters to real jobs."""
        return self.compiled_params.compile_virtual(dependent_jobs)
