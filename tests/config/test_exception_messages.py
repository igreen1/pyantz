"""Test that errors say what is wrong."""

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from pyantz.infrastructure.config import (
    InitialConfig,
    JobConfig,
    JobPipeline,
    VirtualJobConfig,
)
from pyantz.infrastructure.runner._remotes.container import run_container
from pyantz.infrastructure.runner._remotes.ssh import run_ssh

NOP = "pyantz.jobs.testing.nop.do_nothing"


def _config(host: dict[str, str]) -> InitialConfig[Any]:
    return InitialConfig.model_validate(
        {
            "jobs": [{"function": NOP, "parameters": {}}],
            "submitter": {"type_": "local_proc", "working_directory": "/tmp"},  # noqa: S108
            "host": host,
        },
    )


def test_container_runner_names_the_wrong_host() -> None:
    """Giving the container runner an ssh host says so."""
    config = _config({"type_": "ssh", "remote_host": "h"})

    with pytest.raises(RuntimeError, match=r"'container' host, got 'ssh'"):
        run_container(config)


def test_ssh_runner_names_the_wrong_host() -> None:
    """Giving the ssh runner a local host says so."""
    config = _config({"type_": "local"})

    with pytest.raises(RuntimeError, match=r"'ssh' host, got 'local'"):
        run_ssh(config)


def test_non_virtual_function_is_explained() -> None:
    """Using a normal parameter model as a virtual job explains the requirement."""

    class NotVirtual(BaseModel):
        def compile_virtual(self, deps: list[JobConfig]) -> list[JobConfig]:
            return deps

    with pytest.raises(ValidationError, match="mark_virtual"):
        VirtualJobConfig(function=NotVirtual, parameters={})


def test_pipeline_must_be_iterable() -> None:
    """A pipeline given as a number says what it got."""

    class Holder(BaseModel):
        jobs: JobPipeline

    with pytest.raises(TypeError, match="must be a list of jobs, got int"):
        Holder.model_validate({"jobs": 5})
