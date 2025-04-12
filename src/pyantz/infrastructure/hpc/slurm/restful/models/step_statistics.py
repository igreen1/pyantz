"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_statistics"""

from typing import Optional

from pydantic import BaseModel

from .step_statistics_cpu import StepStatisticsCpu
from .step_statistics_energy import StepStatisticsEnergy


class StepStatistics(BaseModel):
    """v0.0.42 STEP_STATISTICS"""

    CPU: Optional[StepStatisticsCpu]
    energy: Optional[StepStatisticsEnergy]
