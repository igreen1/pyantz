"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_timeouts"""

from typing import Optional

from pydantic import BaseModel

from .uint16_no_val_struct import Uint16NoValStruct


class PartitionInfoTimeouts(BaseModel):
    """v0.0.42 PARTITION_INFO_TIMEOUTS"""

    resume: Optional[Uint16NoValStruct]
    suspend: Optional[Uint16NoValStruct]
