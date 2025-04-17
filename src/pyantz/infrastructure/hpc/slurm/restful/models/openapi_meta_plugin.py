"""https://slurm.schedmd.com/rest_api.html#v0_0_42_openapi_meta_plugin"""

from typing import Optional

from pydantic import BaseModel, Field


class OpenapiMetaPlugin(BaseModel):
    """v0.0.42 OPENAPI_META_PLUGIN"""

    type_: Optional[str] = Field(..., alias="type")
    name: Optional[str]
    data_parser: Optional[str]
    accounting_storage: Optional[str]
