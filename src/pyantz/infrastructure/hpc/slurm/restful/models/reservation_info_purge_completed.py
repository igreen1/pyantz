"""https://slurm.schedmd.com/rest_api.html#v0_0_42_reservation_info_purge_completed"""

from typing import Optional

from pydantic import BaseModel

from .uint32_no_val_struct import Uint32NoValStruct


class ReservationInfoPurgeCompleted(BaseModel):
    """v0.0.42 RESERVATION_INFO_PURGE_COMPLETED"""

    time: Optional[Uint32NoValStruct]
