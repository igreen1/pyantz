"""Edit files in place."""

import json
import logging
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, JsonValue

from pyantz.infrastructure.config import add_parameters, no_submit_fn

# pattern to find backets with an integer in them
BRACKET_PATTERN: re.Pattern[str] = re.compile(r"\[([\d+\*])\]")


class EditJsonParams(BaseModel):
    """Parameters to edit json."""

    file: Path

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


@add_parameters(EditJsonParams)
@no_submit_fn
def edit_json(params: EditJsonParams) -> bool:  # noqa: C901
    """Edit a .json file in place."""
    logger = logging.getLogger(__name__)

    # create closures so they have access to the params
    # while only currently used for `extra_field`
    # it is likely future users will want more options for editing the json
    # so placing in closures for future capabilities

    def _edit_any(val: JsonValue, field: str, new_value: JsonValue) -> JsonValue:
        if field == "":
            return new_value
        if isinstance(val, dict):
            return _edit_map(val, field, new_value)
        if isinstance(val, (list)):
            return _edit_list(val, field, new_value)

        # the user has specified a "field"
        # but the object is a simple primitive... this is a weird mismatch
        # there are a few ways to handle this but none of them are great
        # so we expose the options to the user
        if params.extra_field == "ignore":
            return val
        if params.extra_field == "overwrite":
            return new_value

        # "force_object" option selected
        field_components = field.split(".")
        curr_field = field_components[0]
        next_field = ".".join(field_components[1:])
        return {curr_field: _edit_any(val, next_field, new_value)}

    def _edit_map(
        val: dict[str, JsonValue], field: str, new_value: JsonValue
    ) -> dict[str, JsonValue]:
        """Update a map based on the field."""
        # first find the correct field substring
        # because fields in a json may contain "." characters, which can be confusing
        # so we must find the longest substring which is present in the dictionary
        # and then pass the remaining components as the field to be edited
        field_components = field.split(".")
        split_idx = -1
        key: str | None = None
        for end_idx in range(len(field_components) - 1, 0, -1):
            sub_field = ".".join(field_components[0:end_idx])
            if sub_field in val:
                key = sub_field
                split_idx = end_idx
                break

        if key is None or split_idx < 0:
            msg = "Cannot find %s in json"
            raise RuntimeError(msg, field)

        return {
            k: (
                _edit_any(
                    v, ".".join(field_components[split_idx:]), new_value=new_value
                )
                if k == key
                else v  # no edits to be made
            )
            for k, v in val.items()
        }

    def _edit_list(
        val: list[JsonValue],
        field: str,
        new_value: JsonValue,
    ) -> list[JsonValue]:
        """Update a list.

        Few different possibilities:
        1. Field = "[i]..." - edit ith element
        2. Field = "abc" - edit all elements, with this field passed to them
        3. Field = "[*]" - replace eaceh element with value

        """
        if match := BRACKET_PATTERN.match(field):
            # user has used [] notation to mark specific elements for updates

            # convenience variables for clarity
            idx: str | int = match.group(1)
            remaining_field = field[3:]
            if idx != "*":
                idx = int(idx)

            def idx_match(curr_idx: int) -> bool:
                """Return if this index of the list is marked for edits."""
                return idx in {"*", curr_idx}

            return [
                _edit_any(item, remaining_field, new_value)
                if idx_match(item_idx)
                else item
                for item_idx, item in enumerate(val)
            ]

        # possibility (2) from the docstring
        # user did not specify how to edit the elements
        # so we assume they want each element to be edited as the field/value specify
        return [_edit_any(item, field, new_value) for item in val]

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

    for field, value in params.updates.items():
        contents = _edit_any(contents, field, value)

    try:
        with params.file.open("w", encoding="utf-8") as fh:
            json.dump(contents, fh)
    except OSError as exc:
        logger.exception("Error while writing file", exc_info=exc)
        return False
    else:
        return True
