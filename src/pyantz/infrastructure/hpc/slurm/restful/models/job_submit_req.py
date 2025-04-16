"""https://slurm.schedmd.com/rest_api.html#v0.0.42_job_submit_req"""

from typing import Optional

from pydantic import BaseModel

from .job_desc_msg import JobDescMsg


class JobSubmitReq(BaseModel):
    """v0.0.42 Job Submit Request"""

    script: Optional[str]  # deprecated
    jobs: Optional[list[JobDescMsg]]
    job: Optional[JobDescMsg]
