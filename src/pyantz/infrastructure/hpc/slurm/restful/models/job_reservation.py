"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_reservation"""

from typing import Optional

from pydantic import BaseModel


class JobReservation(BaseModel):
    """v0.0.42 JOB_RESERVATION"""

    id: Optional[int]
    name: Optional[str]
