"""Test variables are resolved in parameters correctly."""

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

    assert result == {
        "run_dir": "output/run_1/hello"
    }


def test_double_nested_variables() -> None:
    """Test the variables can contain variables and it will resolve properly."""
    variables: dict[str, Any] = {
        "output_dir": "output/run_%{pipeline_id}",
        "pipeline_id": "a_%{run_id}",
        "run_id": 10
    }

    parameters = {"run_dir": "%{output_dir}/hello"}

    result, _ = resolve_parameters(parameters, variables=variables)

    assert result == {
        "run_dir": "output/run_a_10/hello"
    }


def test_whole_variable_preserves_type() -> None:
    """A parameter that is exactly one variable reference keeps the original type."""
    variables: dict[str, Any] = {"n": 5, "flag": True, "items": [1, 2]}

    parameters = {"n": "%{n}", "flag": "%{flag}", "items": "%{items}", "embedded": "x_%{n}"}

    result, remaining = resolve_parameters(parameters, variables=variables)

    assert result == {
        "n": 5,
        "flag": True,
        "items": [1, 2],
        "embedded": "x_5",
    }
    assert remaining is False


def test_missing_whole_variable_flagged() -> None:
    """A whole-variable reference that is missing is left unchanged and flagged."""
    variables: dict[str, Any] = {}
    parameters = {"n": "%{missing}"}

    result, remaining = resolve_parameters(parameters, variables=variables)

    assert result == {"n": "%{missing}"}
    assert remaining is True
