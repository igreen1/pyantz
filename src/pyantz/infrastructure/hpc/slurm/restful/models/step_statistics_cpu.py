"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_statistics_CPU"""

from typing import Optional

from pydantic import BaseModel


class StepStatisticsCpu(BaseModel):
    """v0.0.42 STEP_STATISTICS_CPU"""

    actual_frequency: Optional[int]
