"""https://slurm.schedmd.com/rest_api.html#v0.0.42_assoc_rec_set"""

from typing import Optional

from pydantic import BaseModel

from .tres import Tres
from .uint32_no_val_struct import Uint32NoValStruct


class AssocRecSet(BaseModel):
    """v0.0.42 ASSOC_REC_SET"""

    comment: Optional[str]
    defaultqos: Optional[str]
    grpjobs: Optional[Uint32NoValStruct]
    grpjobsaccrue: Optional[Uint32NoValStruct]
    grpsubmitjobs: Optional[Uint32NoValStruct]
    grptres: Optional[list[Tres]]
    grptresmins: Optional[list[Tres]]
    grptresrunmins: Optional[list[Tres]]
    grpwall: Optional[Uint32NoValStruct]
    maxjobs: Optional[Uint32NoValStruct]
    maxjobsaccrue: Optional[Uint32NoValStruct]
    maxsubmitjobs: Optional[Uint32NoValStruct]
    maxtresminsperjob: Optional[list[Tres]]
    maxtresrunminsperjob: Optional[list[Tres]]
    maxtresrunmins: Optional[list[Tres]]
    maxtresperjob: Optional[list[Tres]]
    maxtrespernode: Optional[list[Tres]]
    maxwalldurationperjob: Optional[Uint32NoValStruct]
    minpriothresh: Optional[Uint32NoValStruct]
    parent: Optional[str]
    priority: Optional[Uint32NoValStruct]
    qoslevel: Optional[str]
    fairshare: Optional[int]
