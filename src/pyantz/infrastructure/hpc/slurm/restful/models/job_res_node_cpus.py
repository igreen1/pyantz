"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_res_node_cpus"""

from typing import Optional

from pydantic import BaseModel


class JobResNodeCpus(BaseModel):
    """v0.0.42 JOB_RES_NODE_CPUS"""

    count: Optional[int]
    used: Optional[int]
