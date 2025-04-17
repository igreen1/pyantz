"""https://slurm.schedmd.com/rest_api.html#v0_0_42_partition_info_accounts"""

from typing import Optional

from pydantic import BaseModel


class PartitionInfoAccounts(BaseModel):
    """v0.0.42 PARTITION_INFO_ACCOUNTS"""

    allowed: Optional[str]
    deny: Optional[str]
