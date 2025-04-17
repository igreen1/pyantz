"""https://slurm.schedmd.com/rest_api.html#v0_0_42_openapi_meta_slurm"""

from typing import Optional

from pydantic import BaseModel

from .openapi_meta_slurm_version import OpenapiMetaSlurmVersion


class OpenapiMetaSlurm(BaseModel):
    """v0.0.42 OPENAPI_META_SLURM"""

    version: Optional[OpenapiMetaSlurmVersion]
    release: Optional[str]
    cluster: Optional[str]
