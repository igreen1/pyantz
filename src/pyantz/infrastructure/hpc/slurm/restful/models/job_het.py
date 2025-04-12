"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_het"""

from typing import Optional

from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct


class JobHet(BaseModel):
    """v0.0.42 JOB_HET"""

    job_id: Optional[int]
    job_offset: Optional[Uint32NoValStruct]
