"""The frontend's idea of the config models matches the backend's."""

from __future__ import annotations

import pytest

from pyantz.infrastructure.config import InitialConfig, JobConfig
from pyantz.infrastructure.config.runners import LocalRunnerConfig, SlurmRunnerConfig
from pyantz.infrastructure.config.virtual import VirtualJobConfig

MODELS = {
    "JobConfig": JobConfig,
    "VirtualJobConfig": VirtualJobConfig,
    "LocalRunnerConfig": LocalRunnerConfig,
    "SlurmRunnerConfig": SlurmRunnerConfig,
    "InitialConfig": InitialConfig,
}


@pytest.mark.parametrize("name", MODELS)
def test_fields_are_the_same(name: str, model_fields: dict[str, list[str]]) -> None:
    """A field added on one side only fails this: update both, or the editor loses it.

    The editor lists the fields in ``frontend/pyantz/src/model/types.ts``.
    """
    assert model_fields[name] == sorted(MODELS[name].model_fields)


def test_every_model_is_checked(model_fields: dict[str, list[str]]) -> None:
    """The frontend does not know a model which these tests don't compare."""
    assert set(model_fields) == set(MODELS)
