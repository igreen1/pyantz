"""Test converting job functions to and from importable names."""

from typing import Any

import pytest

from pyantz.infrastructure.config import JobConfig, JobWithContext, fn_utils
from pyantz.infrastructure.config.fn_utils import (
    import_module_item_by_name,
    serialize_function,
)
from pyantz.virtual.add_variables import AddVariables

NOP = "pyantz.jobs.testing.nop.do_nothing"


def test_lambda_is_not_serializable() -> None:
    """A lambda can't be imported again, which is reported clearly."""
    with pytest.raises(ValueError, match=r"not importable; define it at module level"):
        serialize_function(lambda: 1)


def test_nested_function_is_not_serializable() -> None:
    """A function defined inside another function is reported clearly."""

    def inner() -> None: ...

    with pytest.raises(ValueError, match=r"inner.*not importable"):
        serialize_function(inner)


def test_module_level_function_round_trips() -> None:
    """Module level functions serialize to a name which imports the same function."""
    fn = import_module_item_by_name(NOP)
    assert serialize_function(fn) == NOP
    assert import_module_item_by_name(serialize_function(fn)) is fn


def test_class_methods_can_be_imported() -> None:
    """`package.module.Class.method` finds the method on the class."""
    item = import_module_item_by_name(
        "pyantz.virtual.add_variables.AddVariables.compile_virtual"
    )
    assert item is AddVariables.compile_virtual
    assert (
        import_module_item_by_name("pyantz.virtual.add_variables.AddVariables")
        is AddVariables
    )


def test_from_config_does_not_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """Adding context to a job reuses its function rather than importing it again."""
    config = JobConfig.model_validate(
        {"job_id": "a", "function": NOP, "parameters": {"x": 1}, "depends_on": ["b"]},
    )
    names_imported: list[str] = []
    real_import = fn_utils.import_module_item_by_name

    def _spy(key: Any) -> Any:  # noqa: ANN401
        if isinstance(key, str):
            names_imported.append(key)
        return real_import(key)

    monkeypatch.setattr(fn_utils, "import_module_item_by_name", _spy)

    with_context = JobWithContext.from_config(config)

    assert not names_imported
    assert with_context.function is config.function
    assert with_context.job_id == "a"
    assert with_context.parameters == {"x": 1}
    assert with_context.depends_on == {"b"}
    assert with_context.variables is None


def test_from_config_keeps_existing_variables() -> None:
    """Converting a job that already has context keeps its variables."""
    original = JobWithContext.model_validate(
        {"function": NOP, "parameters": {}, "variables": {"v": 1}},
    )
    assert JobWithContext.from_config(original) == original
