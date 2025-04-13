"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_res_nodes"""

from typing import Optional

from pydantic import BaseModel, Field

from .job_res_node import JobResNode


class JobResNodes(BaseModel):
    """v0.0.42 JOB_RES_NODES"""

    count: Optional[int]
    select_type: Optional[list[str]]
    list_: Optional[str] = Field(..., alias="list")
    whole: Optional[bool]
    allocation: Optional[list[JobResNode]]
