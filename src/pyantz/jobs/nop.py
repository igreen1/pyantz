"""Do nothing

Sometimes the syntax requires something to be filled in, but we
    don't want to do anything

In those cases, use a NOP
"""

import logging

from pyantz.infrastructure.config.base import ParametersType, simple_job
from pyantz.infrastructure.core.status import Status


@simple_job
def nop(_parameters: ParametersType, _logger: logging.Logger) -> Status:
    """Do nothing"""
    return Status.SUCCESS
