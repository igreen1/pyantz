"""Edit files in place."""

import json
import logging
import re
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    WithJsonSchema,
    field_serializer,
)
from ruamel.yaml import YAML

from pyantz.infrastructure.config import add_parameters, no_submit_fn
from pyantz.infrastructure.config.fn_utils import (
    import_function_by_name,
    serialize_function,
)

# pattern to find backets with an integer in them
BRACKET_PATTERN: re.Pattern[str] = re.compile(r"\[([\d+\*])\]")


class _EditJsonLikeParams(BaseModel):
    """Parameters to edit a JSON-like input file."""

    model_config = ConfigDict(frozen=True)

    file: Path

    # updates to be made to the file
    # to edit a subfield, use "." to join fields
    # for example "a.b" will edit the b field in the object pointed to by "a"
    # but, if the JSOn object contains a field "a.b", that will be edited instead
    # to edit arrays, use [] notation, with an index
    # so for example "a.[0]" will edit the 0th element of a
    # but again, if the JSON object contains a field "a.[0]" that will be edited instead
    updates: Mapping[str, Any]


class EditJsonParams(_EditJsonLikeParams):
    """Parameters to edit json."""


class EditYamlParams(_EditJsonLikeParams):
    """Parameters to edit a yaml file."""


@add_parameters(EditYamlParams)
@no_submit_fn
def edit_yaml(params: EditYamlParams) -> bool:
    """Edit a .yaml file in place."""
    logger = logging.getLogger(__name__)

    if not params.file.exists():
        logger.error("No such file %s", params.file)
        return False
    if not params.file.is_file():
        logger.error("Path is not a file. %s", params.file)
        return False

    yaml = YAML()

    try:
        contents = yaml.load(params.file)
        updated_contents = _edit_jsonlike(params, contents)
        yaml.dump(updated_contents, params.file)
    except OSError as exc:
        logger.exception("Error while writing file", exc_info=exc)
        return False
    else:
        return True


@add_parameters(EditJsonParams)
@no_submit_fn
def edit_json(params: EditJsonParams) -> bool:
    """Edit a .json file in place."""
    logger = logging.getLogger(__name__)

    if not params.file.exists():
        logger.error("No such file %s", params.file)
        return False
    if not params.file.is_file():
        logger.error("Path is not a file. %s", params.file)
        return False

    try:
        with params.file.open("r", encoding="utf-8") as fh:
            contents = json.load(fh)
    except OSError as exc:
        logger.exception("Unknown error", exc_info=exc)
        return False

    updated_contents = _edit_jsonlike(params, contents)

    try:
        with params.file.open("w", encoding="utf-8") as fh:
            json.dump(updated_contents, fh)
    except OSError as exc:
        logger.exception("Error while writing file", exc_info=exc)
        return False
    else:
        return True


def _edit_jsonlike(params: _EditJsonLikeParams, contents: JsonValue) -> JsonValue:
    """Edit a JSON like value and return the contents."""
    edit_jsonvalue = _json_editor_factory()

    for field, value in params.updates.items():
        contents = edit_jsonvalue(contents, field, value)

    return contents


class _FunctionDefinition[T: Callable[..., Any]](BaseModel):
    """Quick definition of a function to be run."""

    model_config = ConfigDict(frozen=True)

    kwargs: dict[str, Any] = Field(default_factory=dict)

    args: tuple[Any, ...] = Field(default_factory=tuple)

    func: Annotated[
        T,
        BeforeValidator(import_function_by_name),
        WithJsonSchema(
            {
                "type": "string",
                "format": "base64",
            }
        ),
    ]

    @field_serializer("func")
    def serialize_job_function(
        self,
        fn: T,
    ) -> str:
        """Serialize the fucntion."""
        return serialize_function(fn)


class EditExternalParams(BaseModel):
    """Edit a file using an external function to extract and to save off."""

    # will accept the args/kwargs provded
    # MUST return a JsonValue to be edited
    extract_function: _FunctionDefinition[Callable[..., JsonValue]]

    # the FIRST argument back to this function will be the file being edited
    # afterwards, it will spread the user provided kwargs/args
    save_function: _FunctionDefinition[Callable[..., None]]

    # updates to be made to the file
    # to edit a subfield, use "." to join fields
    # for example "a.b" will edit the b field in the object pointed to by "a"
    # but, if the JSOn object contains a field "a.b", that will be edited instead
    # to edit arrays, use [] notation, with an index
    # so for example "a.[0]" will edit the 0th element of a
    # but again, if the JSON object contains a field "a.[0]" that will be edited instead
    updates: Mapping[str, Any]

    # what to do when the field provided points to a loction that doesn't exist in json
    # for example, consider field = "a.b.c.d" being set to "goodbye!"
    # but the object looks like {"a": "hello world"}
    # what do we do?
    # ignore: return the original if a path doesn't match. Return = {"a": "hello world"}
    # overwrite: follow as much as possible, then overwrite the leaf.
    #       Return = {"a": "goodbye!"}  # noqa: ERA001
    # force_object: add the path. Return = {"a": {"b": {"c": {"d": "goodbye!"}}}}
    extra_field: Literal["ignore", "overwrite", "force_object"]


@add_parameters(EditExternalParams)
@no_submit_fn
def edit_external_method(params: EditExternalParams) -> bool:
    """Edit a file using user-provided functionality."""
    logger = logging.getLogger(__name__)

    try:
        extract_meth = params.extract_function
        extract_result = extract_meth.func(*extract_meth.args, **extract_meth.kwargs)
    except Exception as exc:
        logger.exception(
            "Unknown error while running extraction, cannot continue",
            exc_info=exc,
        )
        return False

    update_fn = _json_editor_factory()

    try:
        contents = extract_result
        for field, value in params.updates.items():
            contents = update_fn(contents, field, value)
    except Exception as exc:
        logger.exception(
            "Error while updateing JsonValue - check that is a properly formed json",
            exc_info=exc,
        )
        return False

    try:
        save_meth = params.save_function
        save_meth.func(contents, *save_meth.args, **save_meth.kwargs)
    except Exception as exc:
        logger.exception("Unknown error while saving results, not saved", exc_info=exc)
        return False

    return True


def _json_editor_factory(  # noqa: C901
) -> Callable[[JsonValue, str, JsonValue], JsonValue]:
    """Create a callable to edit a JsonValue recursively.

    Args:
        extra_field: user has defined a field (nested too deeply); how to handle
            ignore: don't overwrite, ignore the user instructions
            overwrite: return the value as is
            force_objecct: turn the value into an object that is as nested as user input

    """

    def split_components(field: str) -> list[str]:
        """Split on `.` but allow escaping with backslash."""
        field_components = field.split(".")
        # handle escape '.', which are not counted as splitting
        prev: int | None = None
        for i in reversed(range(len(field_components))):
            if field_components[i][-1] == "\\":
                prev_str = field_components.pop(prev) if prev is not None else ""
                field_components[i] = field_components[i][:-1] + "." + prev_str
            prev = i
        return field_components

    def edit_list(
        val: JsonValue, curr_key: str, new_value: JsonValue, field_components: list[str]
    ) -> list[JsonValue]:
        """Edit the value as a list."""
        curr_key = curr_key[1:-1]  # strip []
        if not isinstance(val, Iterable):
            return [
                edit_any({}, field_components=field_components, new_value=new_value)
            ]
        val_as_list: list[JsonValue] = list(val)
        if curr_key == "*":
            return [
                edit_any(item, field_components=field_components, new_value=new_value)
                for item in val_as_list
            ]
        curr_idx = int(curr_key)
        if curr_idx < 0:
            return [
                edit_any({}, field_components=field_components, new_value=new_value),  # type: ignore  # noqa: PGH003
                *val_as_list,
            ]
        if curr_idx >= len(val_as_list):
            return [
                *val_as_list,
                edit_any({}, field_components=field_components, new_value=new_value),  # type: ignore  # noqa: PGH003
            ]
        return [
            *val_as_list[:curr_idx],
            edit_any(val_as_list[curr_idx], field_components, new_value),  # type: ignore  # noqa: PGH003
            *val_as_list[curr_idx + 1 :],
        ]

    def edit_map(
        val: JsonValue,
        curr_key: str,
        new_value: str,
        field_components: list[str],
    ) -> Mapping[str, Any]:
        """Edit the map."""
        if not isinstance(val, Mapping):
            val = {}  # overwrite always
        old_val = val.get(curr_key, {})
        return {
            **{k: v for k, v in val.items() if k != curr_key},
            curr_key: edit_any(  # type: ignore  # noqa: PGH003
                old_val, field_components, new_value
            ),
        }

    def edit_any(
        val: JsonValue, field_components: list[str], new_value: JsonValue
    ) -> JsonValue:
        """Edit any json value that comes our way."""
        if len(field_components) == 0:
            return new_value
        curr_key = field_components[0]
        if curr_key.startswith("[") and curr_key.endswith("]"):
            fn = edit_list
        else:
            fn = edit_map  # type: ignore # noqa: PGH003

        return fn(
            val,
            curr_key,
            new_value,  # type: ignore  # noqa: PGH003
            field_components=field_components[1:],
        )

        return None

    def edit_any_wrapper(val: JsonValue, field: str, new_value: JsonValue) -> JsonValue:
        """Edit any but accept a user style field string that is then split."""
        return edit_any(
            val=val, field_components=split_components(field), new_value=new_value
        )

    return edit_any_wrapper
