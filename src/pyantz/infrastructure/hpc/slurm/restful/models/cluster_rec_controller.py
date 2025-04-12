"""https://slurm.schedmd.com/rest_api.html#v0_0_42_cluster_rec_controller"""

from typing import Optional

from pydantic import BaseModel


class ClusterRecController(BaseModel):
    """0.0.42 CLUSTER_REC_CONTROLLER"""

    host: Optional[str]
    port: Optional[int]
