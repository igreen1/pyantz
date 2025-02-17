"""Run a general config, which is a pipeline with a scope (variables)"""

import logging
from typing import Callable

from pyantz.infrastructure.config.base import Config
from pyantz.infrastructure.core.pipeline import run_pipeline


def run_manager(
    config: Config, submit_fn: Callable[[Config], None], logger: logging.Logger
) -> None:
    """Run the configuration"""
    logger.debug("Manager starting up pipeline with id %d", config.config.id)
    run_pipeline(
        config=config.config,
        variables=config.variables,
        submit_fn=submit_fn,
        logger=logger,
    )
