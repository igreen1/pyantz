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
