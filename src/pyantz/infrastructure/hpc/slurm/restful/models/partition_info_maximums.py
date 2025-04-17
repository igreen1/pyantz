"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_maximums"""

from typing import Optional

from pydantic import BaseModel

from .partition_info_maximums_oversubscribe import PartitionInfoMaximumsOversubscribe
from .uint16_no_val_struct import Uint16NoValStruct
from .uint32_no_val_struct import Uint32NoValStruct
from .uint64_no_val_struct import Uint64NoValStruct


class PartitionInfoMaximums(BaseModel):
    """v0.0.42 PARTITION_INFO_MAXIMUMS"""

    cpus_per_node: Optional[Uint32NoValStruct]
    cpus_per_socker: Optional[Uint32NoValStruct]
    memory_per_cpu: Optional[int]
    partition_memory_per_cpu: Optional[Uint64NoValStruct]
    partition_memory_per_node: Optional[Uint64NoValStruct]
    nodes: Optional[Uint32NoValStruct]
    shares: Optional[int]
    oversubscribe: Optional[PartitionInfoMaximumsOversubscribe]
    time: Optional[Uint32NoValStruct]
    over_time_limit: Optional[Uint16NoValStruct]
