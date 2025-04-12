"""https://slurm.schedmd.com/rest_api.html#v0_0_42_job_desc_msg_rlimits"""

from typing import Optional

from pydantic import BaseModel, Field

from .uint64_no_val_struct import Uint64NoValStruct


class JobDescMsgRlimits(BaseModel):
    """v0.0.42 JOB_DESC_MSG_RLIMITS"""

    cpu: Optional[Uint64NoValStruct]
    fsize: Optional[Uint64NoValStruct]
    data: Optional[Uint64NoValStruct]
    stack: Optional[Uint64NoValStruct]
    core: Optional[Uint64NoValStruct]
    rss: Optional[Uint64NoValStruct]
    nproc: Optional[Uint64NoValStruct]
    nofile: Optional[Uint64NoValStruct]
    memlock: Optional[Uint64NoValStruct]
    as_: Optional[Uint64NoValStruct] = Field(alias="as")
