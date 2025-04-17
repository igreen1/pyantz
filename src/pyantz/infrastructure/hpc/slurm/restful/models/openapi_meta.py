"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_meta"""

from typing import Optional

from pydantic import BaseModel

from .openapi_meta_client import OpenapiMetaClient
from .openapi_meta_plugin import OpenapiMetaPlugin
from .openapi_meta_slurm import OpenapiMetaSlurm


class OpenapiMeta(BaseModel):
    """v0.042 OPENAPI_META"""

    plugin: Optional[OpenapiMetaPlugin]
    client: Optional[OpenapiMetaClient]
    command: Optional[list[str]]
    slurm: Optional[OpenapiMetaSlurm]
