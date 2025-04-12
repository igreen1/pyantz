"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_step"""

from typing import Optional

from pydantic import BaseModel


class StepStep(BaseModel):
    """v0.0.42 STEP_STEP"""

    id: Optional[str]
    name: Optional[str]
