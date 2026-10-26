"""Job that does nothing, mostly for debugging and testing."""

from __future__ import annotations

from typing import Any


def do_nothing(*_: Any, **__: Any) -> bool:  # noqa: ANN401
    """Do nothing and return success.

    Unlike most jobs this function is not registered with
    :func:`~pyantz.infrastructure.config.add_parameters`, so it accepts any
    parameters and ignores them.

    Args:
        *_: ignored positional arguments (a job is given its parameters and a
            submit function).
        **__: ignored keyword arguments.

    Parameters:
        any: every parameter is accepted and ignored.

    Returns:
        bool: always True.

    Raises:
        None: this job never fails.

    Example:
        .. testcode::

            from pyantz.jobs.testing.nop import do_nothing

            assert do_nothing({"hello": "there"}, lambda job: None)

        .. testoutput::

            did nothing :)

    """
    print("did nothing :)")  # noqa: T201
    return True
