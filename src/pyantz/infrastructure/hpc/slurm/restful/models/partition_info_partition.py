"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_partition"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoPartition(BaseModel):
    """v0.0.42 PARTITION_INFO_PARTITION"""

    state: Optional[list[str]]
