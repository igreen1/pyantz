"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_CPU"""

from typing import Optional

from pydantic import BaseModel

from .step_cpu_requested_frequency import StepCpuRequestedFrequency


class StepCpu(BaseModel):
    """v0.0.42 STEP_CPU"""

    requested_frequency: Optional[StepCpuRequestedFrequency]
    governor: Optional[str]
