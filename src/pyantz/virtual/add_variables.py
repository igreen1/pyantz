"""Add a variale to the pipeline."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import JobConfig, mark_virtual


@mark_virtual
class AddVariables(BaseModel):
    """Parameters to add a variable."""

    model_config = ConfigDict(frozen=True)

    # variables to add to subsequent jobs
    variables: Mapping[str, Any]

    def compile_virtual(self, deps: list[JobConfig]) -> list[JobConfig]:
        """Create a concrete list of job configs."""
        configs = [
            {
                "function": "pyantz.jobs.wrappers.variables.run_jobs_in_context",
                "parameters": {"jobs": deps, "shared_variables": self.variables},
            }
        ]
        return [JobConfig.model_validate(config) for config in configs]
