"""Test removing `format` from json schemas of the api."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from pyantz.api.endpoints.get_parameters.endpoints import strip_format


def test_format_is_removed_inside_any_of() -> None:
    """Alternatives in a list are cleaned too."""
    schema: dict[str, Any] = {
        "anyOf": [
            {"type": "string", "format": "path"},
            {"type": "string"},
            {"type": "null"},
        ],
    }

    assert strip_format(schema) == {
        "anyOf": [{"type": "string"}, {"type": "string"}, {"type": "null"}],
    }


def test_nested_lists_and_objects() -> None:
    """Lists inside objects inside lists are all followed."""
    schema: dict[str, Any] = {
        "properties": {
            "a": {
                "oneOf": [
                    {"allOf": [{"type": "string", "format": "uri"}]},
                    {"type": "integer", "format": "int64"},
                ],
            },
        },
        "prefixItems": [{"type": "string", "format": "date"}],
    }

    cleaned = strip_format(schema)

    assert cleaned["properties"]["a"]["oneOf"] == [
        {"allOf": [{"type": "string"}]},
        {"type": "integer", "format": "int64"},  # only string formats are stripped
    ]
    assert cleaned["prefixItems"] == [{"type": "string"}]


def test_real_model_schema_has_no_string_formats() -> None:
    """A model with a `Path | str` field no longer exposes `format: path`."""
    from pathlib import Path  # noqa: PLC0415

    class Model(BaseModel):
        location: Path | str

    cleaned = strip_format(Model.model_json_schema())

    assert "format" not in str(cleaned)


def test_scalars_and_original_are_untouched() -> None:
    """Other values are returned as is and the input is not modified."""
    original = {"anyOf": [{"type": "string", "format": "path"}]}

    strip_format(original)

    assert original == {"anyOf": [{"type": "string", "format": "path"}]}
    assert strip_format(None) is None
    assert strip_format("x") == "x"
