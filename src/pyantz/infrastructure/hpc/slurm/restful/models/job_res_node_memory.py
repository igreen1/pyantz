"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_res_node_memory"""

from typing import Optional

from pydantic import BaseModel


class JobResNodeMemory(BaseModel):
    """v0.0.42 JOB_RES_NODE_MEMORY"""

    used: Optional[int]
    allocated: Optional[int]
