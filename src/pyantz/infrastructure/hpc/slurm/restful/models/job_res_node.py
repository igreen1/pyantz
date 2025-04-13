"""https://slurm.schedmd.com/rest_api.html#v0.0.42_job_res_node"""

from typing import Optional

from pydantic import BaseModel

from .job_res_node_cpus import JobResNodeCpus
from .job_res_node_memory import JobResNodeMemory
from .job_res_socket import JobResSocket


class JobResNode(BaseModel):
    """v0.0.42 JOB_RES_NODE"""

    index: int
    name: str
    cpus: Optional[JobResNodeCpus]
    memory: Optional[JobResNodeMemory]
    sockets: list[JobResSocket]
