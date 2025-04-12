"""https://slurm.schedmd.com/rest_api.html#v0_0_42_cluster_rec_associations"""

from typing import Optional

from pydantic import BaseModel

from .assoc_short import AssocShort


class ClusterRecAssociations(BaseModel):
    """v0.0.42 CLUSTER_REC_ASSOCIATIONS"""

    root: Optional[AssocShort]
