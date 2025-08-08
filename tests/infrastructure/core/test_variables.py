"""Test variable resolution module."""

from collections.abc import Mapping

import pytest

from pyantz.infrastructure.config.base import PrimitiveType
from pyantz.infrastructure.core.variables import (
    VARIABLE_PATTERN,
    _resolve_value,
    resolve_variables,
)


def test_regex_pattern() -> None:
    """Test the regex patter gets the correct group(s)."""
    expected_variables_names = {
        "%{a}": ["a"],
        "%{hello there!}": ["hello there!"],
        "%{oh123}": ["oh123"],
        "abc%": [],
        "abc%{hello}": ["hello"],
        "%{1}": ["1"],
        "%{hello}abc": ["hello"],
        "%{hello}a%{bye}": ["hello", "bye"],
    }

    for unparsed, expected in expected_variables_names.items():
        match = [x.lstrip("%{").rstrip("}") for x in VARIABLE_PATTERN.findall(unparsed)]
        assert match == expected


_variables: Mapping[str, PrimitiveType] = {
    "a": 1,
    "b": 2,
    "bb": 12,
    "c": "hello",
    "d": 0.123,
    "e": "true",
    "f": True,
    "g": False,
    "h": "faLsE",
}

_expected = {
    "hello%{b}": "hello2",
    "%{a}": 1,
    "%{b}bye": "2bye",
    "abc%{c}def": "abchellodef",
    "%{b}": 2,
    "%{d}": 0.123,
    "hello%{d}": "hello0.123",
    "%{h}": False,
    "%{g}": False,
    "%{f}": True,
    "%{e}": True,
    "helo%{e}": "helotrue",
    "a%{f}b": "aTrueb",
    "a%{f}b%{d}": "aTrueb0.123",
}


@pytest.mark.parametrize(
    ("given", "expected", "variables"), [(k, v, _variables) for k, v in _expected.items()]
)
def test_simple_variable_replacement(given, expected, variables) -> None:
    """Test a simploe replacement of a variable string."""
    assert _resolve_value(given, variables=variables) == expected


def test_parameters_simple_replacement() -> None:
    """Test a simple interpolation of the variables into parameters."""
    variables = _variables

    expected_values = list(_expected.items())

    input_parameters = {str(i): in_val for i, (in_val, _expected_out) in enumerate(expected_values)}
    output_parameters = {
        str(i): expected_out for i, (_in_val, expected_out) in enumerate(expected_values)
    }

    assert output_parameters == resolve_variables(input_parameters, variables=variables)


def test_parameter_variable_expressions() -> None:
    """Test that expressions are allowed in variables (basic math)."""
    variables = _variables

    expected_values = {
        ("%{a * b}", 2),
        ("%{a + b}", 3),
        ("%{a / b}", 1 / 2),
        ("%{a - b}", -1),
        ("%{a * b - bb}", -10),
        ("%{bb / b * b}", 3),
    }

    input_parameters = {str(i): in_val for i, (in_val, _expected_out) in enumerate(expected_values)}
    output_parameters = {
        str(i): expected_out for i, (_in_val, expected_out) in enumerate(expected_values)
    }

    assert output_parameters == resolve_variables(input_parameters, variables=variables)


def test_nested_variable_resolution() -> None:
    """Test that nested dictionaries and lists are resolved but not if they're a job."""
    variables = _variables
    input_dict = {
        "val": "%{a}",
        "idk": {
            "type": "job",
            "function": "pyantz.jobs.nop.nop",
            "parameters": {
                "test": "%{a}",
            },
        },
        "hello": {
            "there": {
                "general": 1,
                "kenobi": "%{b}",
            },
        },
        "list": {"nested_list": ["%{c}", "there"]},
    }

    expected_dict = {
        "val": 1,
        "idk": {
            "type": "job",
            "function": "pyantz.jobs.nop.nop",
            "parameters": {
                "test": "%{a}",
            },
        },
        "hello": {
            "there": {
                "general": 1,
                "kenobi": 2,
            },
        },
        "list": {"nested_list": ["hello", "there"]},
    }

    output_dict = resolve_variables(input_dict, variables=variables)
    assert output_dict == expected_dict
