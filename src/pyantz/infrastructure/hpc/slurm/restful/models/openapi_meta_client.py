"""https://slurm.schedmd.com/rest_api.html#v0_0_42_openapi_meta_client"""

from typing import Optional

from pydantic import BaseModel


class OpenapiMetaClient(BaseModel):
    """v0.0.42 OPENAPI_META_CLIENT"""

    source: Optional[str]
    user: Optional[str]
    group: Optional[str]
