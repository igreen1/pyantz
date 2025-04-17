"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_tres"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoTres(BaseModel):
    """v0.0.42 PARTITION_INFO_TRES"""

    billing_weights: Optional[str]
    configured: Optional[str]
