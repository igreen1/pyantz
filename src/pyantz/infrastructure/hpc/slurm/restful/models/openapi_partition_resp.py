"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_partition_resp"""

from typing import Optional

from pydantic import BaseModel

from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning
from .partition_info import PartitionInfo
from .uint64_no_val_struct import Uint64NoValStruct


class OpenapiPartitionResp(BaseModel):
    """v0.0.42 OPENAPI_PARTITION_RESP"""

    partitions: list[PartitionInfo]
    last_update: Optional[Uint64NoValStruct]
    meta: Optional[OpenapiMeta]
    error: Optional[list[OpenapiError]]
    warning: Optional[list[OpenapiWarning]]
