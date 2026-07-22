"""Virtual job that injects variables into its dependent jobs.

:class:`AddVariables` is a virtual job — it compiles away at startup and
leaves no footprint at runtime.  Use it in a pipeline to declare shared
variables that should be visible to all subsequent jobs.

Example JSON usage::

    {
      "function": "pyantz.virtual.add_variables.AddVariables",
      "virtual": true,
      "parameters": {
        "variables": {"data_dir": "/mnt/data", "batch_size": 64}
      }
    }
"""

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
        """Wrap *deps* in a :func:`~pyantz.jobs.wrappers.variables.run_jobs_in_context` job.

        Produces a single concrete job that, when executed, injects
        :attr:`variables` into every job in *deps* before submitting them.

        Args:
            deps: The list of downstream jobs that should receive the new
                variables as inherited context.

        Returns:
            A single-element list containing the compiled
            :class:`~pyantz.infrastructure.config.job.JobConfig`.
        """
        configs = [
            {
                "function": "pyantz.jobs.wrappers.variables.run_jobs_in_context",
                "parameters": {"jobs": deps, "shared_variables": self.variables},
            }
        ]
        return [JobConfig.model_validate(config) for config in configs]
