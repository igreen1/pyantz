"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_reservation_resp"""

from typing import Optional

from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning
from .reservation_info import ReservationInfo
from .uint64_no_val_struct import Uint64NoValStruct


class OpenapiReservationResp(BaseModel):
    """v0.0.42 OPENAPI_RESERVATION_RESP"""

    reservations: list[ReservationInfo]
    last_update: Uint64NoValStruct
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
