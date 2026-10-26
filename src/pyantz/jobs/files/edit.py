r"""In-place editing of JSON and YAML files.

Fields are addressed with dot-separated paths (e.g. ``"server.port"``)
and array indices in bracket notation (e.g. ``"items.[0]"``).  Escape a
literal ``.`` with a backslash: ``"a\\.b"`` refers to the key ``a.b``.

Available jobs:

* :func:`edit_json` — edit a ``.json`` file.
* :func:`edit_yaml` — edit a ``.yaml`` / ``.yml`` file.
* :func:`edit_external_method` — edit any format via user-supplied
  extract/save callables.
"""

from __future__ import annotations

import copy
import json
import logging
import tempfile
from collections.abc import Callable, Mapping, MutableMapping
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
)
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from pyantz.infrastructure.config import add_parameters, no_submit_fn
from pyantz.infrastructure.config.fn_utils import ImportedCallable

JSON_INDENT = 2
"""Indentation of the json files which are written."""

type _ExtraField = Literal["ignore", "overwrite", "force_object"]
"""What to do when an update's field doesn't exist in the edited value.

Consider the field ``"a.b.c.d"`` being set to ``"goodbye!"`` in ``{"a": "hello"}``:

* ``ignore``: leave the value as it was: ``{"a": "hello"}``.
* ``overwrite``: follow the field as far as possible, then replace that leaf:
  ``{"a": "goodbye!"}``.
* ``force_object``: create the missing objects:
  ``{"a": {"b": {"c": {"d": "goodbye!"}}}}``.
"""


class _PathMismatchError(Exception):
    """The field being edited does not match the structure of the file."""


class _EditJsonLikeParams(BaseModel):
    """Parameters to edit a JSON-like input file."""

    model_config = ConfigDict(frozen=True)

    file: Path
    """File to edit in place."""

    updates: Mapping[str, Any]
    r"""Updates to make, mapping each field to its new value.

    To edit a subfield, join fields with ``.`` (escape a literal ``.`` with
    ``\\``): ``"a.b"`` edits the ``b`` field of the object in ``a``. To edit
    arrays, use ``[]`` with an index: ``"a.[0]"`` edits the first element of
    ``a``. An index past the end appends, a negative index adds to the front and
    ``"[*]"`` edits every element.
    """

    extra_field: _ExtraField = "force_object"
    """What to do when a field doesn't exist in the file: ``ignore`` leaves the
    value as it was, ``overwrite`` replaces the deepest existing leaf, and
    ``force_object`` creates the missing objects."""


class EditJsonParams(_EditJsonLikeParams):
    """Parameters to edit json."""


class EditYamlParams(_EditJsonLikeParams):
    """Parameters to edit a yaml file."""


@add_parameters(EditYamlParams)
@no_submit_fn
def edit_yaml(params: EditYamlParams) -> bool:
    r"""Edit a .yaml file in place.

    The file is edited with ``ruamel.yaml``, which keeps its comments and the
    order of its keys. It is written atomically, so a failure leaves the original
    intact.

    Args:
        params: the job's parameters, validated as :class:`EditYamlParams`.

    Parameters:
        file (Path): file to edit in place.
        updates (Mapping[str, Any]): new values keyed by their field, such as
            ``"a.b"`` or ``"items.[0]"``; see :class:`EditJsonParams`.
        extra_field (str): what to do when a field doesn't exist: ``ignore``,
            ``overwrite`` or ``force_object``. Defaults to ``force_object``.

    Returns:
        bool: True if the file was edited, False if it doesn't exist, isn't a
        file, can't be parsed or a field is invalid.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testsetup:: files-edit-yaml

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-edit-yaml

            from pathlib import Path

            from pyantz.jobs.files.edit import edit_yaml

            Path("config.yaml").write_text("server:\n  port: 80  # the port\n")
            edit_yaml(
                {"file": "config.yaml", "updates": {"server.port": 8080}},
                lambda job: None,
            )
            print(Path("config.yaml").read_text(), end="")

        .. testoutput:: files-edit-yaml

            server:
              port: 8080 # the port

        .. testcleanup:: files-edit-yaml

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
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
        _write_atomically(params.file, lambda fh: yaml.dump(updated_contents, fh))
    except (OSError, YAMLError, ValueError) as exc:
        logger.exception("Error while editing %s", params.file, exc_info=exc)
        return False
    else:
        return True


@add_parameters(EditJsonParams)
@no_submit_fn
def edit_json(params: EditJsonParams) -> bool:
    """Edit a .json file in place.

    The file is rewritten with an indent of :data:`JSON_INDENT`. It is written
    atomically, so a failure leaves the original intact.

    Args:
        params: the job's parameters, validated as :class:`EditJsonParams`.

    Parameters:
        file (Path): file to edit in place.
        updates (Mapping[str, Any]): new values keyed by their field, such as
            ``"a.b"`` or ``"items.[0]"``; see :class:`EditJsonParams`.
        extra_field (str): what to do when a field doesn't exist: ``ignore``,
            ``overwrite`` or ``force_object``. Defaults to ``force_object``.

    Returns:
        bool: True if the file was edited, False if it doesn't exist, isn't a
        file, isn't valid json or a field is invalid.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testsetup:: files-edit-json

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-edit-json

            import json
            from pathlib import Path

            from pyantz.jobs.files.edit import edit_json

            Path("data.json").write_text('{"items": [{"n": 1}, {"n": 2}]}')
            edit_json(
                {
                    "file": "data.json",
                    "updates": {"items.[*].n": 0, "items.[5]": "appended"},
                },
                lambda job: None,
            )
            print(json.loads(Path("data.json").read_text()))

        .. testoutput:: files-edit-json

            {'items': [{'n': 0}, {'n': 0}, 'appended']}

        .. testcleanup:: files-edit-json

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
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
        updated_contents = _edit_jsonlike(params, contents)
        _write_atomically(
            params.file,
            lambda fh: json.dump(updated_contents, fh, indent=JSON_INDENT),
        )
    except (OSError, ValueError, TypeError) as exc:  # ValueError: bad json or field
        logger.exception("Error while editing %s", params.file, exc_info=exc)
        return False
    else:
        return True


def _write_atomically(path: Path, write: Callable[[Any], object]) -> None:
    """Write via a temporary file so that a failure leaves the original intact.

    The temporary file is created next to ``path`` and replaces it only once
    ``write`` has finished.

    Args:
        path: the file to (over)write.
        write: function which writes the new contents to the open text file it is
            given.

    Returns:
        None.

    Raises:
        OSError: if the temporary file can't be created or can't replace ``path``.
        BaseException: anything raised by ``write`` is raised again, once the
            temporary file has been removed.

    Example:
        .. testsetup:: files-edit-write

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: files-edit-write

            from pathlib import Path

            from pyantz.jobs.files.edit import _write_atomically

            def fail(fh):
                fh.write("half written")
                raise RuntimeError("oops")

            Path("notes.txt").write_text("original")
            try:
                _write_atomically(Path("notes.txt"), fail)
            except RuntimeError:
                pass
            print(Path("notes.txt").read_text())

        .. testoutput:: files-edit-write

            original

        .. testcleanup:: files-edit-write

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=path.name,
        suffix=".tmp",
        delete=False,
    ) as tmp:
        try:
            write(tmp)
        except BaseException:
            tmp.close()
            Path(tmp.name).unlink(missing_ok=True)
            raise
    Path(tmp.name).replace(path)


def _edit_jsonlike(params: _EditJsonLikeParams, contents: JsonValue) -> JsonValue:
    """Edit a JSON like value and return the contents.

    Args:
        params: parameters holding the updates to make and how to handle fields
            which don't exist.
        contents: the value to edit. Mutable mappings are edited in place.

    Returns:
        JsonValue: the edited value.

    Raises:
        ValueError: if a field is invalid, e.g., it has an empty part (``"a..b"``)
            or a list index which isn't an integer.

    Example:
        .. testcode::

            from pyantz.jobs.files.edit import EditJsonParams, _edit_jsonlike

            params = EditJsonParams(
                file="unused.json",
                updates={"a.b": 1},
                extra_field="overwrite",
            )
            print(_edit_jsonlike(params, {"a": "text"}))

        .. testoutput::

            {'a': 1}

    """
    edit_jsonvalue = _json_editor_factory(params.extra_field)

    for field, value in params.updates.items():
        contents = edit_jsonvalue(contents, field, value)

    return contents


class _FunctionDefinition[T: Callable[..., Any]](BaseModel):
    """Quick definition of a function to be run."""

    model_config = ConfigDict(frozen=True)

    kwargs: dict[str, Any] = Field(default_factory=dict)
    """Keyword arguments to call the function with."""

    args: tuple[Any, ...] = Field(default_factory=tuple)
    """Positional arguments to call the function with."""

    func: ImportedCallable[T]
    """The function to call, given by its full import path."""


class EditExternalParams(BaseModel):
    """Edit a file using an external function to extract and to save off."""

    extract_function: _FunctionDefinition[Callable[..., JsonValue]]
    """Function called with its args/kwargs to load the value to edit; it MUST
    return a JsonValue."""

    save_function: _FunctionDefinition[Callable[..., None]]
    """Function called to save the edited value: its FIRST argument is the edited
    value, followed by its own args/kwargs."""

    updates: Mapping[str, Any]
    r"""Updates to make, mapping each field to its new value.

    To edit a subfield, join fields with ``.`` (escape a literal ``.`` with
    ``\\``): ``"a.b"`` edits the ``b`` field of the object in ``a``. To edit
    arrays, use ``[]`` with an index: ``"a.[0]"`` edits the first element of
    ``a``. An index past the end appends, a negative index adds to the front and
    ``"[*]"`` edits every element.
    """

    extra_field: _ExtraField = "force_object"
    """What to do when a field doesn't exist in the file: ``ignore`` leaves the
    value as it was, ``overwrite`` replaces the deepest existing leaf, and
    ``force_object`` creates the missing objects."""


@add_parameters(EditExternalParams)
@no_submit_fn
def edit_external_method(params: EditExternalParams) -> bool:
    """Edit a file using user-provided functionality.

    The value to edit is loaded by ``extract_function``, edited like
    :func:`edit_json` would, and given to ``save_function``. This edits formats
    which have no job of their own.

    Args:
        params: the job's parameters, validated as :class:`EditExternalParams`.

    Parameters:
        extract_function (dict): ``func`` (import path), ``args`` and ``kwargs``
            of the function which returns the value to edit.
        save_function (dict): ``func`` (import path), ``args`` and ``kwargs`` of
            the function which saves the edited value, given as its first
            argument.
        updates (Mapping[str, Any]): new values keyed by their field, such as
            ``"a.b"`` or ``"items.[0]"``; see :class:`EditExternalParams`.
        extra_field (str): what to do when a field doesn't exist: ``ignore``,
            ``overwrite`` or ``force_object``. Defaults to ``force_object``.

    Returns:
        bool: True if the value was extracted, edited and saved; False if any of
        those steps fails.

    Raises:
        None: failures are logged and reported by returning False.

    Example:
        .. testcode::

            from pyantz.jobs.files.edit import edit_external_method

            edit_external_method(
                {
                    "extract_function": {"func": "json.loads", "args": ['{"a": 1}']},
                    "save_function": {"func": "builtins.print"},
                    "updates": {"b": 2},
                },
                lambda job: None,
            )

        .. testoutput::

            {'a': 1, 'b': 2}

    """
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

    update_fn = _json_editor_factory(params.extra_field)

    try:
        contents = extract_result
        for field, value in params.updates.items():
            contents = update_fn(contents, field, value)
    except Exception as exc:
        logger.exception(
            "Error while updating JsonValue - check that is a properly formed json",
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


def _json_editor_factory(  # noqa: C901, PLR0915
    extra_field: _ExtraField = "force_object",
) -> Callable[[JsonValue, str, JsonValue], JsonValue]:
    """Create a callable to edit a JsonValue recursively.

    The callable takes the value to edit, a field such as ``"a.[0].b"`` and the
    new value, and returns the edited value. Mutable mappings are edited in place
    (keeping the order of keys and, for yaml, comments), except with ``ignore``,
    which edits a copy so the original is untouched when a field doesn't match.

    Args:
        extra_field: user has defined a field (nested too deeply); how to handle
            ignore: don't overwrite, ignore the user instructions
            overwrite: follow as far as possible, then overwrite the leaf
            force_object: turn the value into an object that is as nested as user input

    Returns:
        Callable[[JsonValue, str, JsonValue], JsonValue]: the editing function.

    Raises:
        None: errors in fields are raised by the returned function, as
            ``ValueError``.

    Example:
        .. testcode::

            from pyantz.jobs.files.edit import _json_editor_factory

            for extra_field in ("ignore", "overwrite", "force_object"):
                edit = _json_editor_factory(extra_field)
                print(extra_field, edit({"a": "hello"}, "a.b.c", "goodbye!"))

        .. testoutput::

            ignore {'a': 'hello'}
            overwrite {'a': 'goodbye!'}
            force_object {'a': {'b': {'c': 'goodbye!'}}}

    """

    def split_components(field: str) -> list[str]:
        r"""Split on `.` but allow escaping with backslash.

        Args:
            field: the field, such as ``"a.b"`` or ``"a\\.b"`` (the key ``a.b``).

        Returns:
            list[str]: the field's parts, with escaped dots kept in them.

        Raises:
            ValueError: if a part is empty, e.g., ``"a..b"``.

        """
        field_components = field.split(".")
        # handle escape '.', which are not counted as splitting
        prev: int | None = None
        for i in reversed(range(len(field_components))):
            if field_components[i].endswith("\\"):
                prev_str = field_components.pop(prev) if prev is not None else ""
                field_components[i] = field_components[i][:-1] + "." + prev_str
            prev = i
        if not all(field_components):
            msg = f"Invalid field {field!r}: it has an empty part (check the dots)"
            raise ValueError(msg)
        return field_components

    def overwrite_on_mismatch() -> bool:
        """Say if a leaf replaces a field that doesn't exist in the edited value.

        Args:
            None.

        Returns:
            bool: True for ``overwrite``, False for ``force_object``.

        Raises:
            _PathMismatchError: the field doesn't exist and extra_field is `ignore`.

        """
        if extra_field == "ignore":
            raise _PathMismatchError
        return extra_field == "overwrite"

    def edit_list(
        val: JsonValue, curr_key: str, new_value: JsonValue, field_components: list[str]
    ) -> list[JsonValue]:
        """Edit the value as a list.

        Args:
            val: the value to edit; if it isn't a list, it is replaced (with
                ``overwrite``) or treated as an empty list.
            curr_key: the list part of the field, such as ``"[0]"``, ``"[-1]"``
                or ``"[*]"``.
            new_value: the value to set at the end of the field.
            field_components: the parts of the field after ``curr_key``.

        Returns:
            list[JsonValue]: the edited list (a new list).

        Raises:
            ValueError: if the index isn't an integer or ``*``.
            _PathMismatchError: if ``val`` isn't a list and extra_field is
                ``ignore``.

        """
        curr_key = curr_key[1:-1]  # strip []
        if not isinstance(val, list):
            if overwrite_on_mismatch():
                return cast("list[JsonValue]", new_value)
            val = []
        val_as_list: list[JsonValue] = list(val)
        if curr_key == "*":
            return [
                edit_any(item, field_components=field_components, new_value=new_value)
                for item in val_as_list
            ]
        curr_idx = int(curr_key)
        if curr_idx < 0:
            return [
                edit_any({}, field_components=field_components, new_value=new_value),
                *val_as_list,
            ]
        if curr_idx >= len(val_as_list):
            if field_components and overwrite_on_mismatch():
                return [*val_as_list, new_value]
            return [
                *val_as_list,
                edit_any({}, field_components=field_components, new_value=new_value),
            ]
        return [
            *val_as_list[:curr_idx],
            edit_any(val_as_list[curr_idx], field_components, new_value),
            *val_as_list[curr_idx + 1 :],
        ]

    def edit_map(
        val: JsonValue,
        curr_key: str,
        new_value: JsonValue,
        field_components: list[str],
    ) -> JsonValue:
        """Edit the map.

        Args:
            val: the value to edit; if it isn't a mapping, it is replaced (with
                ``overwrite``) or treated as an empty mapping.
            curr_key: the key to edit.
            new_value: the value to set at the end of the field.
            field_components: the parts of the field after ``curr_key``.

        Returns:
            JsonValue: the edited mapping (``val`` itself if it is mutable).

        Raises:
            _PathMismatchError: if the field doesn't exist and extra_field is
                ``ignore``.

        """
        if not isinstance(val, Mapping):
            if overwrite_on_mismatch():
                return new_value
            val = {}
        current = cast("Mapping[str, Any]", val)
        if field_components and curr_key not in current and overwrite_on_mismatch():
            edited = new_value
        else:
            edited = edit_any(current.get(curr_key, {}), field_components, new_value)
        if isinstance(current, MutableMapping):
            # edit in place: keeps the order of the keys and, for yaml, the comments
            cast("MutableMapping[str, Any]", current)[curr_key] = edited
            return cast("JsonValue", current)
        return cast("JsonValue", {**current, curr_key: edited})

    def edit_any(
        val: JsonValue, field_components: list[str], new_value: JsonValue
    ) -> JsonValue:
        """Edit any json value that comes our way.

        Args:
            val: the value to edit.
            field_components: the remaining parts of the field; when empty,
                ``new_value`` replaces ``val``.
            new_value: the value to set at the end of the field.

        Returns:
            JsonValue: the edited value.

        Raises:
            ValueError: if a list index isn't an integer or ``*``.
            _PathMismatchError: if the field doesn't exist and extra_field is
                ``ignore``.

        """
        if len(field_components) == 0:
            return new_value
        curr_key = field_components[0]
        if curr_key.startswith("[") and curr_key.endswith("]"):
            fn: Callable[..., JsonValue] = edit_list
        else:
            fn = edit_map

        return fn(
            val,
            curr_key,
            new_value,
            field_components=field_components[1:],
        )

    def edit_any_wrapper(val: JsonValue, field: str, new_value: JsonValue) -> JsonValue:
        """Edit any but accept a user style field string that is then split.

        Args:
            val: the value to edit.
            field: the field to edit, such as ``"a.[0].b"``.
            new_value: the value to set at the field.

        Returns:
            JsonValue: the edited value; with ``ignore``, the original value if
            the field doesn't match it.

        Raises:
            ValueError: if the field is invalid.

        """
        components = split_components(field)
        if extra_field != "ignore":
            return edit_any(val=val, field_components=components, new_value=new_value)
        # edits happen in place, so work on a copy to leave the original untouched
        try:
            return edit_any(
                val=copy.deepcopy(val),
                field_components=components,
                new_value=new_value,
            )
        except _PathMismatchError:
            return val

    return edit_any_wrapper
