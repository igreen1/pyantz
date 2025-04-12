"""https://slurm.schedmd.com/rest_api.html#v0.0.42_step"""

from typing import Optional

from pydantic import BaseModel

from .process_exit_code_verbose import ProcessExitCodeVerbose
from .step_cpu import StepCpu
from .step_nodes import StepNodes
from .step_statistics import StepStatistics
from .step_step import StepStep
from .step_task import StepTask
from .step_tasks import StepTasks
from .step_time import StepTime
from .step_tres import StepTres


class Step(BaseModel):
    """v0.0.42 STEP"""

    time: Optional[StepTime]
    exit_code: Optional[ProcessExitCodeVerbose]
    nodes: Optional[StepNodes]
    tasks: Optional[StepTasks]
    pid: Optional[str]
    CPU: Optional[StepCpu]
    kill_request_user: Optional[str]
    state: Optional[list[str]]
    statistics: Optional[StepStatistics]
    step: Optional[StepStep]
    task: Optional[StepTask]
    tres: Optional[StepTres]
