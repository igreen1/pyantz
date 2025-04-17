"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_nodes"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoNodes(BaseModel):
    """v0.0.42_partition_info_nodes"""

    allowed_allocation: Optional[str]
    configured: Optional[str]
    total: Optional[int]
