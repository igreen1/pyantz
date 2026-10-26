"""Test variables are resolved in parameters correctly."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyantz.infrastructure.config.variables import resolve_parameters

if TYPE_CHECKING:
    from typing import Any


def test_variable_variables() -> None:
    """Test the variables can contain variables and it will resolve properly."""
    variables: dict[str, Any] = {
        "output_dir": "output/run_%{pipeline_id}",
        "pipeline_id": 1,
    }

    parameters = {"run_dir": "%{output_dir}/hello"}

    result, _ = resolve_parameters(parameters, variables=variables)

    assert result == {"run_dir": "output/run_1/hello"}


def test_double_nested_variables() -> None:
    """Test the variables can contain variables and it will resolve properly."""
    variables: dict[str, Any] = {
        "output_dir": "output/run_%{pipeline_id}",
        "pipeline_id": "a_%{run_id}",
        "run_id": 10,
    }

    parameters = {"run_dir": "%{output_dir}/hello"}

    result, _ = resolve_parameters(parameters, variables=variables)

    assert result == {"run_dir": "output/run_a_10/hello"}


def test_several_variables_in_one_string_are_resolved() -> None:
    """Several references in one string resolve without being reported unresolved.

    Replacing one reference changes the string's length; this used to misplace the
    others and report a variable as unresolved even though all of them were set.
    """
    variables: dict[str, Any] = {"a": 1, "bb": "x", "nested": "%{a}%{a}"}

    result, unresolved = resolve_parameters(
        {"path": "%{bb}-%{a}/%{nested}-%{bb}"}, variables=variables
    )

    assert result == {"path": "x-1/11-x"}
    assert unresolved is False


def test_unset_variable_next_to_set_ones_is_reported() -> None:
    """An unset reference stays as written and is reported, the others resolve."""
    result, unresolved = resolve_parameters(
        {"path": "%{a}/%{unset}/%{a}"}, variables={"a": "set"}
    )

    assert result == {"path": "set/%{unset}/set"}
    assert unresolved is True
