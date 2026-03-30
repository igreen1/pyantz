"""Configuration of a virtual job."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from .fn_utils import import_module_item_by_name
from .job import AbstractJobConfig, JobConfig

if TYPE_CHECKING:
    from . import JobConfig


class VirtualParamModel(BaseModel):
    """Model to be inherited by parameters of virtual jobs.

    Virtual jobs have no functions, so they are purely defined by
    these parameter models, which will compile into a real set of
    job configs (which will primarily focus on the parameters).
    """

    model_config = ConfigDict(frozen=True)

    @abstractmethod
    def compile_virtual(self, dependent_jobs: list[JobConfig]) -> list[JobConfig]:
        """Compile our job into a list of real jobs."""


class VirtualJobConfig(AbstractJobConfig):
    """A job which is only used to create an ordered set of 'real' jobs."""

    model_config = ConfigDict(frozen=True)

    # name, which points to the name of the Parameters to be used
    name: str

    virtual: Literal[True] = True

    @property
    def param_model(self) -> type[VirtualParamModel]:
        """Model of the parameters to use to compile to real jobs."""
        return import_module_item_by_name(self.name)

    @property
    def compiled_params(self) -> VirtualParamModel:
        """Build our parameters."""
        return self.param_model.model_validate(self.parameters)

    def compile_virtual(self, dependent_jobs: list[JobConfig]) -> list[JobConfig]:
        """Compile from our parameters to real jobs."""
        return self.compiled_params.compile(dependent_jobs)
