"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_cpus"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoCpus(BaseModel):
    """v0.0.42 PARTITION_INFO_CPUS"""

    task_binding: Optional[int]
    total: Optional[int]
