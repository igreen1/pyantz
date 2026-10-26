"""Test that cyclic variable references raise instead of hanging."""

# regression tests for issue #21

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from pyantz.infrastructure.config import JobWithContext
from pyantz.infrastructure.config.variables import resolve_var_any
from pyantz.infrastructure.runner.job_manager import JobVariables, run_job_with_details
from pyantz.jobs.wrappers.loops import local_for_loop

if TYPE_CHECKING:
    from pathlib import Path

TOUCH = "pyantz.jobs.testing.touch_file.touch_file"


def test_self_referential_variable_raises() -> None:
    """A variable containing a reference to itself raises rather than hanging."""
    with pytest.raises(ValueError, match="Recursive variable reference"):
        resolve_var_any("%{a}", {"a": "%{a}"})


def test_cyclic_variables_raise() -> None:
    """Variables forming a cycle raise rather than hanging."""
    with pytest.raises(ValueError, match="Recursive variable reference"):
        resolve_var_any("x_%{a}", {"a": "%{b}", "b": "%{a}"})


def test_nested_references_still_resolve() -> None:
    """Legitimate chains of references are fully resolved."""
    result, unresolved = resolve_var_any("%{a}", {"a": "%{b}/x", "b": "root"})
    assert result == "root/x"
    assert not unresolved


def test_job_with_cyclic_variables_fails_instead_of_raising() -> None:
    """Running a job whose variables form a cycle reports a failure."""
    job = JobWithContext(
        function="pyantz.jobs.testing.nop.do_nothing",
        parameters={"path": "%{a}"},
        variables={"a": "%{a}"},
    )

    result = run_job_with_details(job, lambda _child, _parent: None)

    assert not result.success
    assert "Recursive variable reference" in (result.details or "")


def test_loop_goes_on_after_a_job_with_cyclic_variables(tmp_path: Path) -> None:
    """With stop_on_failure off, a cyclic variable doesn't end the loop."""
    token = JobVariables.set({"a": "%{a}"})
    try:
        success = local_for_loop(
            {
                "num_iterations": 2,
                "stop_on_failure": False,
                "jobs": [
                    {"function": TOUCH, "parameters": {"path": "%{a}"}},
                    {
                        "function": TOUCH,
                        "parameters": {
                            "path": os.fspath(tmp_path / "ok_%{loop_index}"),
                        },
                    },
                ],
            },
            lambda _job: None,
        )
    finally:
        JobVariables.reset(token)

    assert not success
    assert sorted(path.name for path in tmp_path.iterdir()) == ["ok_0", "ok_1"]
