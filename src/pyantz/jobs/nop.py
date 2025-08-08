"""Do nothing.

Sometimes the syntax requires something to be filled in, but we
    don't want to do anything

In those cases, use a NOP
"""

import logging

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


@config_base.simple_job(None)
def nop(_parameters: config_base.ParametersType, _logger: logging.Logger) -> Status:
    """Do nothing."""
    return Status.SUCCESS
