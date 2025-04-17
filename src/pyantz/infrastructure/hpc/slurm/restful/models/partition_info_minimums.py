"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_minimums"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoMinimums(BaseModel):
    """v0.0.42 PARTITION_INFO_MINIMUMS"""

    nodes: Optional[int]
