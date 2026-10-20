"""Test variable resolution inside different kinds of values."""

from collections import OrderedDict, namedtuple

from pydantic import BaseModel

from pyantz.infrastructure.config.variables import resolve_var_any

VARIABLES = {"x": "1"}


class _Model(BaseModel):
    value: str


def test_builtin_containers_keep_their_type() -> None:
    """Lists, tuples, sets and frozensets are resolved and stay what they were."""
    for container in (list, tuple, set, frozenset):
        original = container(["a_%{x}", "b"])

        resolved, unresolved = resolve_var_any(original, VARIABLES)

        assert type(resolved) is container
        assert set(resolved) == {"a_1", "b"}
        assert not unresolved


def test_nested_values_are_resolved() -> None:
    """Containers inside containers inside mappings are all searched."""
    resolved, _ = resolve_var_any({"a": [("%{x}", {"b": ["%{x}"]})]}, VARIABLES)

    assert resolved == {"a": [("1", {"b": ["1"]})]}


def test_unresolved_flag_comes_from_any_depth() -> None:
    """A missing variable anywhere is reported."""
    _, unresolved = resolve_var_any({"a": [{"b": "%{missing}"}]}, VARIABLES)

    assert unresolved


def test_other_values_are_left_alone() -> None:
    """Models, bytes, ranges, generators and paths aren't taken apart or consumed."""
    model = _Model(value="%{x}")
    generator = (i for i in range(3))
    values = [model, b"%{x}", range(3), generator, 5, None, 2.5]

    for value in values:
        resolved, unresolved = resolve_var_any(value, VARIABLES)

        assert resolved is value
        assert not unresolved
    assert list(generator) == [0, 1, 2]  # not consumed


def test_namedtuple_does_not_raise() -> None:
    """Types which can't be rebuilt from a list fall back to the builtin."""
    point = namedtuple("point", ["a", "b"])  # noqa: PYI024

    resolved, _ = resolve_var_any(point("%{x}", "y"), VARIABLES)

    assert tuple(resolved) == ("1", "y")


def test_ordered_mapping_content_is_kept() -> None:
    """Mappings are resolved into a dict with the same order and values."""
    resolved, _ = resolve_var_any(OrderedDict([("b", "%{x}"), ("a", "z")]), VARIABLES)

    assert list(resolved.items()) == [("b", "1"), ("a", "z")]


def test_empty_containers() -> None:
    """Empty containers come back empty and are not unresolved."""
    for empty in ([], (), set(), frozenset(), {}):
        resolved, unresolved = resolve_var_any(empty, VARIABLES)

        assert resolved == empty
        assert not unresolved
