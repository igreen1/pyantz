"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_info_power"""

from typing import Any, Optional

from pydantic import BaseModel


class JobInfoPower(BaseModel):
    """v0.0.42 JOB_INFO_POWER"""

    flags: Optional[list[Any]]
