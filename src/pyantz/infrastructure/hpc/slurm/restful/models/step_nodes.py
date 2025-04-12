"""https://slurm.schedmd.com/rest_api.html#v0_0_42_step_nodes"""

from typing import Optional

from pydantic import BaseModel


class StepNodes(BaseModel):
    """v0.0.42 STEP_NODES"""

    count: Optional[int]
    range: Optional[str]
    list: Optional[list[str]]
