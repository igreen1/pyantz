"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_tres"""

from typing import Optional

from pydantic import BaseModel

from .tres import Tres


class JobTres(BaseModel):
    """v0.0.42 JOB_TRES"""

    allocated: Optional[list[Tres]]
    requested: Optional[list[Tres]]
