"""Test editing a yaml file."""

from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from pyantz.jobs.files.edit import edit_yaml

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


def test_simple_yaml(tmp_path: Path) -> None:
    """Test editing a quick-n-easy yaml."""
    contents = {"hello": "world"}

    file_path = tmp_path / "tmp_file.yaml"

    with file_path.open("w", encoding="utf-8") as fh:
        YAML().dump(contents, stream=fh)

    params: dict[str, Any] = {
        "file": file_path,
        "updates": {
            "hello": "general kenobi",
        },
    }

    edit_yaml(params, None)

    assert file_path.read_text(encoding="utf-8").rstrip() == "hello: general kenobi"


def test_nested_yaml(tmp_path: Path) -> None:
    """Test editing a nested yaml configuration."""
    contents: dict[str, Any] = {
        "angles": {
            "left": [0, 70, 90],
            "right": {"semi": 10, "hemi": 210},
        },
        "generals": [
            {
                "name": "kenobi",
            },
            {
                "name": "skywalker",
            },
        ],
    }

    file_path = tmp_path / "tmp_file.yaml"
    with file_path.open("w", encoding="utf-8") as fh:
        YAML().dump(contents, stream=fh)

    params: dict[str, Any] = {
        "file": file_path,
        "updates": {
            "new_field.new_subfield": "value1",
            "angles.left.[1]": 10,
            "angles.right.hemi": 20,
            "generals.[1].name": "vader",
            "new_afield\\.cool": "hello",
            "generals.[3]": {"name": "why hello"}
        },
    }
    expected_contents: dict[str, Any] = {
        "angles": {
            "left": [0, 10, 90],
            "right": {"semi": 10, "hemi": 20},
        },
        "generals": [
            {
                "name": "kenobi",
            },
            {
                "name": "vader",
            },
            {
                "name": "why hello",
            }
        ],
        "new_field": {"new_subfield": "value1"},
        "new_afield.cool": "hello"
    }

    edit_yaml(
        params,
        None,
    )

    with file_path.open("r", encoding="utf-8") as fh:
        results = YAML().load(fh)
    assert expected_contents == results
