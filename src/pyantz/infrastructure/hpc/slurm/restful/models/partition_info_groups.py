"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_groups"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoGroups(BaseModel):
    """v0.0.42 PARTITION_INFO_GROUPS"""

    allowed: Optional[str]
