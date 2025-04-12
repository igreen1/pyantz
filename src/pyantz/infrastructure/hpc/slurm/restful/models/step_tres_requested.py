"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_tres_requested"""

from typing import Optional

from pydantic import BaseModel

from .tres import Tres


class StepTresRequested(BaseModel):
    """v0.0.42 STEP_TRES_REQUESTED"""

    max: Optional[list[Tres]]
    min: Optional[list[Tres]]
    average: Optional[list[Tres]]
    total: Optional[list[Tres]]
