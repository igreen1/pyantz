"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_comment"""

from typing import Optional

from pydantic import BaseModel


class JobComment(BaseModel):
    """v0.0.42 JOB_COMMENT"""

    administrator: Optional[str]
    job: Optional[str]
    system: Optional[str]
