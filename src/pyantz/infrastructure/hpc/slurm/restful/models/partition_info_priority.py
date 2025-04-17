"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_priority"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoPriority(BaseModel):
    """v0.0.42 PARTITION_INFO_PRIORITY"""

    job_factor: Optional[int]
    tier: Optional[int]
