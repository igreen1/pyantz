"""https://slurm.schedmd.com/rest_api.html#__Models"""

from typing import Optional

from pydantic import BaseModel

from .instance_time import InstanceTime


class Instance(BaseModel):
    """v0.0.42 INSTANCE"""

    cluster: Optional[str]
    extra: Optional[str]
    instance_id: Optional[str]
    instance_type: Optional[str]
    node_name: Optional[str]
    time: Optional[InstanceTime]
