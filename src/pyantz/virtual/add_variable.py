"""Add a variale to the pipeline."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from pyantz.jobs.wrappers.variables import run_jobs_in_context, VariableContextParams
from pyantz.infrastructure.config import JobConfig, mark_virtual


@mark_virtual
class AddVariableParameters(BaseModel):

    model_config = ConfigDict(frozen=True)

    # variables to add to subsequent jobs
    variables: Mapping[str, Any]

    def compile(self, deps: list[JobConfig]) -> JobConfig:
        """"""