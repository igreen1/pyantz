"""https://slurm.schedmd.com/rest_api.html#v0.0.42_job_res"""

from typing import Optional

from pydantic import BaseModel

from .job_res_nodes import JobResNodes
from .uint16_no_val_struct import Uint16NoValStruct


class JobRes(BaseModel):
    """v0.0.42 JOB_RES"""

    select_type: list[str]
    nodes: Optional[JobResNodes]
    cpus: int
    threads_per_core: Uint16NoValStruct
