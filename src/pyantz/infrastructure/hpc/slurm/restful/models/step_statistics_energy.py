"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_statistics_energy"""

from typing import Optional

from pydantic import BaseModel

from .uint64_no_val_struct import Uint64NoValStruct


class StepStatisticsEnergy(BaseModel):
    """v0.0.42 STEP_STATISTICS_ENERGY"""

    consumed: Optional[Uint64NoValStruct]
