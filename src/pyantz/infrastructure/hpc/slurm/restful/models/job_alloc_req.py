"""https://slurm.schedmd.com/rest_api.html#v0.0.42_job_alloc_req"""

from typing import Optional

from pydantic import BaseModel

from .job_desc_msg import JobDescMsg


class JobAllocReq(BaseModel):
    """v0.0.42 JOB_ALLOC_REQ"""

    hetjob: Optional[list[JobDescMsg]]
    job: Optional[JobDescMsg]
