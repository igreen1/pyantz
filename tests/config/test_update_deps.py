"""Test the ``update_deps`` decorator re-maps the dependency graph."""

# regression tests for issue #14

from pydantic import BaseModel

from pyantz.infrastructure.config import JobConfig
from pyantz.infrastructure.config.parameters import update_deps

NOP = "pyantz.jobs.testing.nop.do_nothing"


class _Params(BaseModel):
    """Parameters unused by the identity compilation."""


def _identity(_params: _Params, deps: list[JobConfig]) -> list[JobConfig]:
    """Return the dependencies unchanged."""
    return deps


def _job(job_id: str, depends_on: set[str] | None = None) -> JobConfig:
    return JobConfig.model_validate(
        {
            "job_id": job_id,
            "function": NOP,
            "parameters": {},
            "depends_on": depends_on,
        },
    )


def test_depends_on_follows_new_ids() -> None:
    """A dependent job points at the new id of its dependency."""
    job_a = _job("a")
    job_b = _job("b", {"a"})

    new_a, new_b = update_deps(_identity)(_Params(), [job_a, job_b])

    assert new_a.job_id != "a"
    assert new_b.job_id != "b"
    assert new_a.depends_on is None
    assert new_b.depends_on == {new_a.job_id}


def test_external_dependencies_unchanged() -> None:
    """Dependencies on ids outside of the list are kept as-is."""
    job_a = _job("a", {"external"})
    job_b = _job("b", {"a", "other_external"})

    new_a, new_b = update_deps(_identity)(_Params(), [job_a, job_b])

    assert new_a.depends_on == {"external"}
    assert new_b.depends_on == {new_a.job_id, "other_external"}


def test_wrapper_preserves_function_name() -> None:
    """The decorated function keeps its metadata."""
    assert getattr(update_deps(_identity), "__name__", None) == _identity.__name__
