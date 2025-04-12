"""https://slurm.schedmd.com/rest_api.html#v0.0.42_acct_gather_energy"""

from typing import Optional

from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct


class AcctGatherEnergy(BaseModel):
    """v0.0.42 ACCT_GATHER_ENERGY"""

    average_watts: Optional[int]
    base_consumed_energy: Optional[int]
    consumed_energy: Optional[int]
    current_watts: Optional[Uint32NoValStruct]
    previous_consumed_energy: Optional[int]
    last_collected: Optional[int]
