"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_state"""

from typing import Optional

from pydantic import BaseModel


class JobState(BaseModel):
    """v0.0.42 JOB_STATE"""

    current: Optional[list[str]]
    reason: Optional[str]
