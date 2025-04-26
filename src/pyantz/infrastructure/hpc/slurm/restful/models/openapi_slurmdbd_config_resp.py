"""https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_slurmdbd_config_resp"""

from typing import Optional
from pydantic import BaseModel


from .cluster_rec import ClusterRec
from .tres import Tres
from .account import Account
from .user import User
from .qos import Qos
from .wckey import Wckey
from .assoc import Assoc
from .instance import Instance
from .openapi_error import OpenapiError
from .openapi_meta import OpenapiMeta
from .openapi_warning import OpenapiWarning


class OpenapiSlurmdbdConfigResp(BaseModel):
    """v0.0.42 OPENAPI_SLURMDBD_CONFIG_RESP"""

    clusters: Optional[list[ClusterRec]]
    tres: Optional[list[Tres]]
    accounts: Optional[list[Account]]
    users: Optional[list[User]]
    qos: Optional[list[Qos]]
    wckeys: Optional[list[Wckey]]
    associations: Optional[list[Assoc]]
    instances: Optional[list[Instance]]
    meta: Optional[OpenapiMeta]
    errors: Optional[list[OpenapiError]]
    warnings: Optional[list[OpenapiWarning]]
