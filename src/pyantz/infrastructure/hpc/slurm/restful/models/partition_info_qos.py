"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_qos"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoQos(BaseModel):
    """v0.0.42 PARTITION_INFO_QOS"""

    allowed: Optional[str]
    deny: Optional[str]
    assigned: Optional[str]
