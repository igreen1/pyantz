"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_tres"""

from typing import Optional

from pydantic import BaseModel

from .step_tres_consumed import StepTresConsumed
from .step_tres_requested import StepTresRequested
from .tres import Tres


class StepTres(BaseModel):
    """v0.0.42 STEP_TRES"""

    requested: Optional[StepTresRequested]
    consumed: Optional[StepTresConsumed]
    allocated: Optional[list[Tres]]
