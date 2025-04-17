"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_nodes_resp"""

from typing import Optional

from pydantic import BaseModel

from .node import Node
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning
from .uint64_no_val_struct import Uint64NoValStruct


class OpenapiNodesResp(BaseModel):
    """v0.0.42 OPENAPI_NODES_RESP"""

    nodes: list[Node]
    last_update: Optional[Uint64NoValStruct]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
