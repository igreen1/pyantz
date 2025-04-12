"""https://slurm.schedmd.com/rest_api.html#v0_0_42_assoc_max"""

from typing import Optional

from pydantic import BaseModel

from .assoc_max_jobs import AssocMaxJobs
from .assoc_max_per import AssocMaxPer
from .assoc_max_tres import AssocMaxTres


class AssocMax(BaseModel):
    """v0.0.42 ASSOC_MAX"""

    jobs: Optional[AssocMaxJobs]
    tres: Optional[AssocMaxTres]
    per: Optional[AssocMaxPer]
