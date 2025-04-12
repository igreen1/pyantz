"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_default"""

from typing import Optional

from pydantic import BaseModel


class AssocDefault(BaseModel):
    """v0.0.42 ASSOC_DEFAULT"""

    qos: Optional[str]
