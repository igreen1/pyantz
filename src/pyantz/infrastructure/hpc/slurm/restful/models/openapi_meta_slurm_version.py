"""https://slurm.schedmd.com/rest_api.html#v0_0_42_openapi_meta_slurm_version"""

from typing import Optional

from pydantic import BaseModel


class OpenapiMetaSlurmVersion(BaseModel):
    """v0.0.42 OPENAPI_META_SLURM_VERSION"""

    major: Optional[str]
    micro: Optional[str]
    minor: Optional[str]
