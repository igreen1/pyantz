"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_maximums_oversubscribe"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoMaximumsOversubscribe(BaseModel):
    """v0.0.42 PARTITION_INFO_MAXIMUMS_OVERSUBSCRIBE"""

    jobs: Optional[int]
    flags: Optional[list[str]]
