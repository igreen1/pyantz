"""Job that does nothing, mostly for debugging and testing."""

from typing import Any


def do_nothing(*_: Any, **__: Any) -> bool:  # noqa: ANN401
    """Do nothing and return success."""
    print("did nothing :)")
    return True
