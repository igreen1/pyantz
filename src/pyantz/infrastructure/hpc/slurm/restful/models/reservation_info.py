"""https://slurm.schedmd.com/rest_api.html#v0.0.42_reservation_info"""

from typing import Optional

from pydantic import BaseModel

from .reservation_core_spec import ReservationCoreSpec
from .reservation_info_purge_completed import ReservationInfoPurgeCompleted
from .uint32_no_val_struct import Uint32NoValStruct
from .uint64_no_val_struct import Uint64NoValStruct


class ReservationInfo(BaseModel):
    """v0.0.42 RESERVATION_INFO"""

    accounts: Optional[str]
    burst_buffer: Optional[str]
    core_count: Optional[int]
    core_specializations: Optional[list[ReservationCoreSpec]]
    end_time: Optional[Uint64NoValStruct]
    features: Optional[str]
    flags: Optional[list[str]]
    groups: Optional[str]
    licenses: Optional[str]
    max_start_delay: Optional[int]
    name: Optional[str]
    node_count: Optional[int]
    node_list: Optional[str]
    partition: Optional[str]
    purge_completed: Optional[ReservationInfoPurgeCompleted]
    start_time: Optional[Uint64NoValStruct]
    watts: Optional[Uint32NoValStruct]
    tres: Optional[str]
    users: Optional[str]
