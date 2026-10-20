"""Test editing json and yaml files."""

import json
from typing import TYPE_CHECKING, Any

import pytest
from ruamel.yaml import YAML

from pyantz.jobs.files.edit import (
    EditExternalParams,
    EditJsonParams,
    EditYamlParams,
    edit_external_method,
    edit_json,
    edit_yaml,
)

if TYPE_CHECKING:
    from pathlib import Path


def _edit_json(path: Path, updates: dict[str, Any]) -> bool:
    params = EditJsonParams(file=path, updates=updates).model_dump()
    return edit_json(params, lambda *_: None)


def _edit_yaml(path: Path, updates: dict[str, Any]) -> bool:
    params = EditYamlParams(file=path, updates=updates).model_dump()
    return edit_yaml(params, lambda *_: None)


def test_edit_json_value(tmp_path: Path) -> None:
    """A nested value is changed and the rest kept."""
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"a": {"b": 1, "c": 2}, "d": [1, 2]}))

    assert _edit_json(path, {"a.b": 10, "d.[1]": 20}) is True

    assert json.loads(path.read_text()) == {"a": {"b": 10, "c": 2}, "d": [1, 20]}


def test_key_order_is_kept(tmp_path: Path) -> None:
    """The edited key stays where it was instead of moving to the end."""
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"first": 1, "middle": 2, "last": 3}))

    _edit_json(path, {"middle": 20})

    assert list(json.loads(path.read_text())) == ["first", "middle", "last"]


def test_editing_into_a_string_replaces_it(tmp_path: Path) -> None:
    """Indexing a string does not explode it into characters."""
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"x": "text"}))

    _edit_json(path, {"x.[0]": "new"})

    assert json.loads(path.read_text()) == {"x": ["new"]}


@pytest.mark.parametrize("field", ["a..b", "a.", ".a", ""])
def test_empty_field_parts_fail_cleanly(tmp_path: Path, field: str) -> None:
    """A badly formed field returns False, leaving the file untouched."""
    path = tmp_path / "f.json"
    original = json.dumps({"a": {"b": 1}})
    path.write_text(original)

    assert _edit_json(path, {field: 2}) is False

    assert path.read_text() == original


def test_invalid_json_returns_false(tmp_path: Path) -> None:
    """A file which isn't valid json is a failure, not an exception."""
    path = tmp_path / "f.json"
    path.write_text("{not json")

    assert _edit_json(path, {"a": 1}) is False
    assert path.read_text() == "{not json"


def test_invalid_yaml_returns_false(tmp_path: Path) -> None:
    """A file which isn't valid yaml is a failure, not an exception."""
    path = tmp_path / "f.yaml"
    path.write_text("a: [unclosed\n")

    assert _edit_yaml(path, {"a": 1}) is False


def test_failed_edit_keeps_the_original_file(tmp_path: Path) -> None:
    """A value which can't be written leaves the file as it was."""
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"a": 1}))

    assert _edit_json(path, {"a": {1, 2}}) is False  # sets are not json

    assert json.loads(path.read_text()) == {"a": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["f.json"]  # no temp files left


def test_json_is_written_readably(tmp_path: Path) -> None:
    """The output is indented rather than on a single line."""
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"a": 1}))

    _edit_json(path, {"a": 2})

    assert path.read_text() == '{\n  "a": 2\n}'


def test_yaml_comments_and_order_are_kept(tmp_path: Path) -> None:
    """Editing a yaml value keeps the comments and the order of keys."""
    path = tmp_path / "f.yaml"
    path.write_text("first: 1  # the first\nsecond: 2\nthird: 3\n")

    assert _edit_yaml(path, {"second": 20}) is True

    text = path.read_text()
    assert "# the first" in text
    assert YAML().load(text) == {"first": 1, "second": 20, "third": 3}
    assert text.index("first") < text.index("second") < text.index("third")


@pytest.mark.parametrize(
    ("extra_field", "expected"),
    [
        ("force_object", {"a": {"b": {"c": "bye"}}}),
        ("overwrite", {"a": "bye"}),
        ("ignore", {"a": "hello"}),
    ],
)
def test_extra_field_modes(
    tmp_path: Path, extra_field: str, expected: dict[str, Any]
) -> None:
    """The extra_field option decides what happens to a path that doesn't exist."""
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"a": "hello"}))
    params = EditJsonParams(
        file=path, updates={"a.b.c": "bye"}, extra_field=extra_field
    ).model_dump()

    assert edit_json(params, lambda *_: None) is True

    assert json.loads(path.read_text()) == expected


def test_extra_field_ignore_leaves_other_edits_in_place(tmp_path: Path) -> None:
    """Ignoring one bad path still applies the valid updates."""
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"a": "hello", "x": {"y": 1}}))
    params = EditJsonParams(
        file=path, updates={"a.b": 1, "x.y": 2}, extra_field="ignore"
    ).model_dump()

    assert edit_json(params, lambda *_: None) is True

    assert json.loads(path.read_text()) == {"a": "hello", "x": {"y": 2}}


def test_missing_file_and_directory_fail(tmp_path: Path) -> None:
    """A path which isn't a file fails both editors."""
    assert _edit_json(tmp_path / "missing.json", {"a": 1}) is False
    assert _edit_yaml(tmp_path / "missing.yaml", {"a": 1}) is False
    assert _edit_json(tmp_path, {"a": 1}) is False
    assert _edit_yaml(tmp_path, {"a": 1}) is False


@pytest.mark.parametrize(
    ("original", "updates", "expected"),
    [
        ({"d": [1, 2, 3]}, {"d.[*]": 0}, {"d": [0, 0, 0]}),
        ({"d": [{"x": 1}, {"x": 2}]}, {"d.[*].x": 9}, {"d": [{"x": 9}, {"x": 9}]}),
        ({"d": [1, 2]}, {"d.[5]": 3}, {"d": [1, 2, 3]}),
        ({"d": [1, 2]}, {"d.[-1]": 0}, {"d": [0, 1, 2]}),
        ({"d": "text"}, {"d.[0]": 1}, {"d": [1]}),
        ({"a.b": 1}, {"a\\.b": 2}, {"a.b": 2}),
    ],
)
def test_list_and_escape_edits(
    tmp_path: Path,
    original: dict[str, Any],
    updates: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """Lists can be edited by index or all at once, and dots can be escaped."""
    path = tmp_path / "f.json"
    path.write_text(json.dumps(original))

    assert _edit_json(path, updates) is True

    assert json.loads(path.read_text()) == expected


def extract_fixed() -> dict[str, Any]:
    """Give the content to edit."""
    return {"a": {"b": 1}}


SAVED: list[Any] = []


def save_contents(contents: Any, *_args: Any) -> None:  # noqa: ANN401
    """Remember what was saved."""
    SAVED.append(contents)


def save_fails(_contents: Any) -> None:  # noqa: ANN401
    """Fail to save."""
    msg = "disk full"
    raise OSError(msg)


def test_edit_external_method() -> None:
    """The extracted value is edited and given to the save function."""
    SAVED.clear()
    params = EditExternalParams(
        extract_function={"func": extract_fixed},  # type: ignore[arg-type]
        save_function={"func": save_contents},  # type: ignore[arg-type]
        updates={"a.b": 2, "c": 3},
    )

    assert edit_external_method(params.model_dump(), lambda *_: None) is True

    assert SAVED == [{"a": {"b": 2}, "c": 3}]


def test_edit_external_method_failing_save() -> None:
    """A save which fails fails the job."""
    params = EditExternalParams(
        extract_function={"func": extract_fixed},  # type: ignore[arg-type]
        save_function={"func": save_fails},  # type: ignore[arg-type]
        updates={"a": 1},
    )

    assert edit_external_method(params.model_dump(), lambda *_: None) is False
