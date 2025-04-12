"""https://slurm.schedmd.com/rest_api.html#v0_0_42_process_exit_code_verbose_signal"""

from typing import Optional

from pydantic import BaseModel

from .uint16_no_val_struct import Uint16NoValStruct


class ProcessExitCodeVerboseSignal(BaseModel):
    """v0.0.42 PROCESS_EXIT_CODE_VERBOSE_SIGNAL"""

    id: Optional[Uint16NoValStruct]
    name: Optional[str]
