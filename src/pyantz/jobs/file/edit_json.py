"""Edit a json file by changing a field to a value."""

import json
import logging
import pathlib
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, FilePath

import pyantz.infrastructure.config.base as config_base
from pyantz.infrastructure.core.status import Status


class Parameters(BaseModel, frozen=True):
    """The parameters required for the simple job edit json command."""

    path: str
    field: str
    value: config_base.PrimitiveType | list[config_base.PrimitiveType]


class _RuntimeParameters(BaseModel, frozen=True):
    """Parameters which must be true at runtime.

    Seperation allows for files to not exist until this function is called.
    """

    path: FilePath
    field: str
    value: config_base.PrimitiveType | list[config_base.PrimitiveType]


@config_base.simple_job(Parameters)
def edit_json(parameters: config_base.ParametersType, logger: logging.Logger) -> Status:
    """Edit a json file to set a field with a new value.

    To handle nested objects, make a path of keys with `.` between each field
    For example, to edit the below value
    {
        "field": {
            "nested_field": 1
        }
    }

    edit field "field.nested_field"

    Parameters {
        path (str): path to the json to edit (file must already exist)
        field (str): the field to edit
            if the field doesn't exist, it is inserted into the object
        value (PrimitiveType | list[PrimitiveType]: value to set the field to
    }

    Args:
        parameters (config_base.ParametersType): see above
        logger (logging.Logger): used to log information on the job

    Returns:
        Status: SUCCESS if completed successfully, otherwise false

    """
    params_parsed = _RuntimeParameters.model_validate(parameters)

    json_path: pathlib.Path = pathlib.Path(params_parsed.path)
    try:
        with json_path.open(mode="r", encoding="utf-8") as fh:
            original_json = json.load(fh)
    except FileNotFoundError as exc:
        logger.exception("Unable to find path: %s", json_path, exc_info=exc)
        return Status.ERROR
    except OSError as exc:
        logger.exception("Unable to open json at path: %s", json_path, exc_info=exc)
        return Status.ERROR

    new_json = nested_edit(
        original_json=original_json, key=params_parsed.field, value=params_parsed.value
    )

    try:
        with json_path.open(mode="w", encoding="utf-8") as fh:
            json.dump(new_json, fh)
    except OSError as exc:
        logger.exception("Unable to save json", exc_info=exc)
        logger.critical("JSON edit failed and likely corrupted the original file")
        return Status.ERROR

    return Status.SUCCESS


def nested_edit(
    original_json: Mapping[str, Any],
    key: str,
    value: config_base.PrimitiveType | list[config_base.PrimitiveType],
) -> Mapping[str, Any]:
    """Edit a dictionary by setting the value of field.

    To access nested objects, fields are marked with "."
    However, if a key exists in the dictionary that matches the key (even with .), it will
        be edited

    Note, will perform a shallow copy by copying each level it traverses but not deeper levels
        because it uses the ** operator to copy value and overwrite

    Args:
        original_json
            (Mapping[str, config_base.PrimitiveType | None | list[config_base.PrimitiveType]]):
            the dictionary to edit
        key (str): the key to edit in the original_json
        value (config_base.PrimitiveType | list[config_base.PrimitiveType]): value to set in key

    Returns:
        Mapping[str, config_base.PrimitiveType | list[config_base.PrimitiveType]]: the original json
            with the field edited

    """
    if not isinstance(original_json, dict):
        return nested_edit({}, key, value)

    if key in original_json or "." not in key or key == ".":
        # if already exists, overwrite it
        # or, if we are not nesting anymore
        return {**original_json, key: value}

    outer_field, inner_field = key.split(".", maxsplit=1)

    return {
        **original_json,
        outer_field: nested_edit(original_json.get(outer_field, {}), inner_field, value),
    }
