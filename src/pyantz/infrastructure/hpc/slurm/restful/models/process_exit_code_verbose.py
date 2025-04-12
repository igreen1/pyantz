"""https://slurm.schedmd.com/rest_api.html#v0.0.42_process_exit_code_verbose"""

from typing import Optional

from pydantic import BaseModel

from .process_exit_code_verbose_signal import ProcessExitCodeVerboseSignal
from .uint32_no_val_struct import Uint32NoValStruct


class ProcessExitCodeVerbose(BaseModel):
    """v0.0.42 PROCESS_EXIT_CODE_VERBOSE"""

    status: Optional[list[str]]
    return_code: Optional[Uint32NoValStruct]
    signal: Optional[ProcessExitCodeVerboseSignal]
