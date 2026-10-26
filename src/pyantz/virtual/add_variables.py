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

Example of :class:`AddVariables`:

    .. testsetup:: virtual-add-variables

        import os, shutil, tempfile
        start_dir = os.getcwd()
        os.chdir(tempfile.mkdtemp())

    .. testcode:: virtual-add-variables

        import os

        from pyantz import start

        start(
            {
                "submitter": {
                    "type_": "local_proc",
                    "working_directory": ".",
                    "use_same_proc": True,
                },
                "jobs": [
                    {
                        "job_id": "set_name",
                        "function": "pyantz.virtual.add_variables.AddVariables",
                        "parameters": {"variables": {"name": "results"}},
                    },
                    {
                        "function": "pyantz.jobs.files.simple.mkdir",
                        "parameters": {"dir_path": "%{name}"},
                        "depends_on": ["set_name"],
                    },
                ],
            }
        )
        print(os.path.isdir("results"))

    .. testoutput:: virtual-add-variables

        True

    .. testcleanup:: virtual-add-variables

        tmp = os.getcwd()
        os.chdir(start_dir)
        shutil.rmtree(tmp)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from pyantz.infrastructure.config import JobConfig, mark_virtual


@mark_virtual
class AddVariables(BaseModel):
    """Parameters to add a variable."""

    model_config = ConfigDict(frozen=True)

    variables: Mapping[str, Any]
    """Variables to add to the jobs which depend on this one."""

    def compile_virtual(self, deps: list[JobConfig]) -> list[JobConfig]:
        """Wrap *deps* in a ``run_jobs_in_context`` job.

        Produces a single concrete job that, when executed, injects
        :attr:`variables` into every job in *deps* before submitting them.

        Args:
            deps: The list of downstream jobs that should receive the new
                variables as inherited context.

        Returns:
            A single-element list containing the compiled
            :class:`~pyantz.infrastructure.config.job.JobConfig`.

        Raises:
            pydantic.ValidationError: if the compiled job is invalid.

        Example:
            .. testcode::

                from pyantz.infrastructure.config import JobConfig
                from pyantz.virtual.add_variables import AddVariables

                job = JobConfig(
                    function="pyantz.jobs.testing.nop.do_nothing", parameters={}
                )
                (wrapper,) = AddVariables(variables={"x": 1}).compile_virtual([job])
                print(wrapper.parameters["jobs"][0].job_id == job.job_id)

            .. testoutput::

                True

        """
        configs = [
            {
                "function": "pyantz.jobs.wrappers.variables.run_jobs_in_context",
                "parameters": {"jobs": deps, "shared_variables": self.variables},
            }
        ]
        return [JobConfig.model_validate(config) for config in configs]
