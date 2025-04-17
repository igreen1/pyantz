"""https://slurm.schedmd.com/rest_api.html#v0.0.42_partition_info"""

from typing import Optional

from pydantic import BaseModel

from .partition_info_accounts import PartitionInfoAccounts
from .partition_info_cpus import PartitionInfoCpus
from .partition_info_defaults import PartitionInfoDefaults
from .partition_info_groups import PartitionInfoGroups
from .partition_info_maximums import PartitionInfoMaximums
from .partition_info_minimums import PartitionInfoMinimums
from .partition_info_nodes import PartitionInfoNodes
from .partition_info_partition import PartitionInfoPartition
from .partition_info_priority import PartitionInfoPriority
from .partition_info_qos import PartitionInfoQos
from .partition_info_timeouts import PartitionInfoTimeouts
from .partition_info_tres import PartitionInfoTres
from .uint32_no_val_struct import Uint32NoValStruct


class PartitionInfo(BaseModel):
    """v0.0.42 PARTITION_INFO"""

    nodes: Optional[PartitionInfoNodes]
    accounts: Optional[PartitionInfoAccounts]
    groups: Optional[PartitionInfoGroups]
    qos: Optional[PartitionInfoQos]
    alternate: Optional[str]
    tres: Optional[PartitionInfoTres]
    cluster: Optional[str]
    select_type: Optional[list[str]]
    cpus: Optional[PartitionInfoCpus]
    defaults: Optional[PartitionInfoDefaults]
    grace_time: Optional[int]
    maximums: Optional[PartitionInfoMaximums]
    minimums: Optional[PartitionInfoMinimums]
    name: Optional[str]
    node_sets: Optional[str]
    priority: Optional[PartitionInfoPriority]
    timeouts: Optional[PartitionInfoTimeouts]
    partition: Optional[PartitionInfoPartition]
    suspend_time: Optional[Uint32NoValStruct]
