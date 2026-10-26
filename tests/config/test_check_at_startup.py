"""Test that parameters are only validated at load time when asked for."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from pyantz.infrastructure.config import (
    JobConfig,
    SubmissionFnType,
    add_parameters,
)


class _Params(BaseModel):
    count: int


@add_parameters(_Params)
def _lazy_job(_params: _Params, _submit: SubmissionFnType) -> bool:
    return True


@add_parameters(_Params, check_at_startup=True)
def _eager_job(_params: _Params, _submit: SubmissionFnType) -> bool:
    return True


BAD = {"count": "not a number"}
GOOD = {"count": 3}


def test_default_does_not_validate_at_load() -> None:
    """Without check_at_startup the parameters are validated when the job runs."""
    job = JobConfig(function=_lazy_job, parameters=BAD)
    assert job.parameters == BAD


def test_default_runtime_validation_still_fails_job() -> None:
    """The invalid parameters are still rejected when the job is called."""
    job = JobConfig(function=_lazy_job, parameters=BAD)
    with pytest.raises(ValidationError):
        job.function(job.parameters, lambda _: None)


def test_check_at_startup_rejects_invalid_parameters() -> None:
    """With check_at_startup=True invalid parameters fail at load."""
    with pytest.raises(ValidationError):
        JobConfig(function=_eager_job, parameters=BAD)


def test_check_at_startup_accepts_valid_parameters() -> None:
    """Valid parameters load fine with check_at_startup=True."""
    assert JobConfig(function=_eager_job, parameters=GOOD).parameters == GOOD


def test_strict_validates_at_load() -> None:
    """Strict jobs are validated at load even without the decorator flag."""
    with pytest.raises(ValidationError):
        JobConfig(function=_lazy_job, parameters=BAD, strict=True)
