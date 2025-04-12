"""https://slurm.schedmd.com/rest_api.html#v0.0.42_cluster_rec"""

from typing import Optional

from pydantic import BaseModel

from .cluster_rec_associations import ClusterRecAssociations
from .cluster_rec_controller import ClusterRecController
from .tres import Tres


class ClusterRec(BaseModel):
    """v0.0.42 CLUSTER_REC"""

    controller: Optional[ClusterRecController]
    flags: Optional[list[str]]
    name: Optional[str]
    nodes: Optional[str]
    select_plugin: Optional[str]
    associations: Optional[ClusterRecAssociations]
    rpc_version: Optional[int]
    tres: Optional[list[Tres]]
