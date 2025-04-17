"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_defaults"""

from typing import Optional

from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct
from .uint64_no_val_struct import Uint64NoValStruct


class PartitionInfoDefaults(BaseModel):
    """v0.0.42 PARTITION_INFO_DEFAULTS"""

    memory_per_cpu: Optional[int]
    partition_memory_per_cpu: Optional[Uint64NoValStruct]
    partition_memory_per_node: Optional[Uint64NoValStruct]
    time: Optional[Uint32NoValStruct]
    job: Optional[str]
