"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_required"""

from typing import Optional

from pydantic import BaseModel

from .uint64_no_val_struct import Uint64NoValStruct


class JobRequired(BaseModel):
    """v0.0.42 JOB_REQUIRED"""

    cpus: Optional[int]
    memory_per_cpu: Optional[Uint64NoValStruct]
    memory_per_node: Optional[Uint64NoValStruct]
