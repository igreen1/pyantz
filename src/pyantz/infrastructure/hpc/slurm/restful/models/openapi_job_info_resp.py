"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_job_info_resp"""

from typing import Optional

from pydantic import BaseModel

from .job_info import JobInfo
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning
from .uint64_no_val_struct import Uint64NoValStruct


class OpenapiJobInfoResp(BaseModel):
    """v0.0.42 OPENAPI_JOB_INFO_RESP"""

    jobs: list[JobInfo]
    last_backfill: Uint64NoValStruct
    last_update: Uint64NoValStruct
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
