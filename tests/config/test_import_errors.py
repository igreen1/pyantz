"""Test errors when a function path can't be imported are clear."""

from __future__ import annotations

import pytest

from pyantz.infrastructure.config.fn_utils import import_module_item_by_name


def test_path_without_module_gives_format_hint() -> None:
    """A name with no dot explains the expected format."""
    with pytest.raises(ValueError, match=r"Cannot import 'foo'.*package\.module\.name"):
        import_module_item_by_name("foo")


def test_empty_string_gives_format_hint() -> None:
    """An empty path is also reported as badly formatted."""
    with pytest.raises(ValueError, match="Cannot import ''"):
        import_module_item_by_name("")


def test_missing_module_names_the_module() -> None:
    """A module which doesn't exist is named, and the original error is chained."""
    with pytest.raises(ValueError, match=r"Cannot import 'no_such_pkg\.thing'") as info:
        import_module_item_by_name("no_such_pkg.thing")
    assert isinstance(info.value.__cause__, ImportError)


def test_missing_attribute_names_module_and_attribute() -> None:
    """A typo in the function name says which module lacks which attribute."""
    with pytest.raises(
        ValueError,
        match=r"Module 'pyantz\.jobs\.testing\.nop' has no attribute 'do_nothin'",
    ) as info:
        import_module_item_by_name("pyantz.jobs.testing.nop.do_nothin")
    assert isinstance(info.value.__cause__, AttributeError)


def test_valid_path_and_non_strings_still_work() -> None:
    """Existing behavior is unchanged."""
    fn = import_module_item_by_name("pyantz.jobs.testing.nop.do_nothing")
    assert fn() is True
    assert import_module_item_by_name(fn) is fn
