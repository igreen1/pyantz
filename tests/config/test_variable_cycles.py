"""Test that cyclic variable references raise instead of hanging."""

# regression tests for issue #21

from __future__ import annotations

import pytest

from pyantz.infrastructure.config.variables import resolve_var_any


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
