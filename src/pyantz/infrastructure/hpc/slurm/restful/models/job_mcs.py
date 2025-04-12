"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_mcs"""

from typing import Optional

from pydantic import BaseModel


class JobMcs(BaseModel):
    """v0.0.42 JOB_MCS"""

    label: Optional[str]
