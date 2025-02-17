"""These decorators are added to ANTZ jobs to allow the pydantic models
    to check if the functions are of the correct type to reduce user error
They "mark" a function as a certain type so that at import they can be checked

For example, passing a mutable function to a mutable job will result in a validation
    error at configuration init, hopefully reducing user error

"""

import logging
from typing import Callable, Mapping

# avoid circular imports
from pyantz.infrastructure.config.base import (
    JobFunctionType,
    MutableJobFunctionType,
    ParametersType,
    PipelineConfig,
    PrimitiveType,
    Status,
    SubmitFunctionType,
    SubmitterJobFunctionType,
)


def mutable_job(
    fn: Callable[
        [ParametersType, Mapping[str, PrimitiveType], logging.Logger],
        tuple[Status, Mapping[str, PrimitiveType]],
    ],
) -> MutableJobFunctionType:
    """Wrap a mutable job to
    1. Allow it to accept variable args if a user incorrectly marks job
    2. Allow for type checking in the pydantic model
    """

    def _mutable_job(
        parameters: ParametersType,
        variables: Mapping[str, PrimitiveType],
        logger: logging.Logger,
        *_,
        **__,
    ):
        return fn(parameters, variables, logger)

    _mutable_job.__module__ = fn.__module__
    _mutable_job.__name__ = fn.__name__

    return _mutable_job


def submitter_job(fn: SubmitterJobFunctionType) -> SubmitterJobFunctionType:
    """Wrap a submitter job to
    1. Allow it to accept variable args if a user incorrectly marks job
    2. Allow for type checking in the pydantic model
    """

    def _submitter_job(
        parameters: ParametersType,
        submit_fn: SubmitFunctionType,
        variables: Mapping[str, PrimitiveType],
        pipeline_config: PipelineConfig,
        logger: logging.Logger,
    ):
        return fn(parameters, submit_fn, variables, pipeline_config, logger)

    _submitter_job.__module__ = fn.__module__
    _submitter_job.__name__ = fn.__name__
    return _submitter_job


def simple_job(
    fn: Callable[[ParametersType, logging.Logger], Status],
) -> JobFunctionType:
    """Wrap a simple job to
    1. Allow it to accept variable args if a user incorrectly marks job
    2. Allow for type checking in the pydantic model
    """

    def _simple_job(parameters: ParametersType, logger: logging.Logger, *_, **__):
        return fn(parameters, logger)

    _simple_job.__module__ = fn.__module__
    _simple_job.__name__ = fn.__name__
    return _simple_job
