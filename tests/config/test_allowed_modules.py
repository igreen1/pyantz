"""Test restricting which modules a configuration can import functions from."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from pyantz.infrastructure.config import JobConfig
from pyantz.infrastructure.config.fn_utils import import_module_item_by_name

if TYPE_CHECKING:
    from pathlib import Path

NOP = "pyantz.jobs.testing.nop.do_nothing"


def test_everything_is_allowed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the variable, any importable name works (configs are trusted code)."""
    monkeypatch.delenv("PYANTZ_ALLOWED_MODULES", raising=False)

    assert import_module_item_by_name("os.getcwd") is os.getcwd


def test_names_outside_the_allowlist_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`os.system` can't be imported when only pyantz is allowed."""
    monkeypatch.setenv("PYANTZ_ALLOWED_MODULES", "pyantz")

    with pytest.raises(ValueError, match=r"'os\.system'.*PYANTZ_ALLOWED_MODULES"):
        import_module_item_by_name("os.system")


def test_names_inside_the_allowlist_work(monkeypatch: pytest.MonkeyPatch) -> None:
    """Modules below an allowed prefix, and the prefix itself, are fine."""
    monkeypatch.setenv("PYANTZ_ALLOWED_MODULES", "pyantz, other_package")

    assert callable(import_module_item_by_name(NOP))
    assert import_module_item_by_name("pyantz.jobs.testing.nop") is not None


def test_prefix_must_match_a_whole_module_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`pyantz_evil` is not inside `pyantz`."""
    monkeypatch.setenv("PYANTZ_ALLOWED_MODULES", "pyantz")

    with pytest.raises(ValueError, match="not inside one of the modules allowed"):
        import_module_item_by_name("pyantz_evil.run")


def test_refused_modules_are_never_imported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The check comes before the import, so import side effects don't happen."""
    marker = tmp_path / "imported"
    module = tmp_path / "sneaky_module.py"
    module.write_text(f"open({str(marker)!r}, 'w').close()\ndef run(): ...\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("PYANTZ_ALLOWED_MODULES", "pyantz")

    with pytest.raises(ValueError, match="not inside"):
        import_module_item_by_name("sneaky_module.run")

    assert not marker.exists()
    assert "sneaky_module" not in sys.modules


def test_job_configs_use_the_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """A config naming a disallowed function fails validation."""
    monkeypatch.setenv("PYANTZ_ALLOWED_MODULES", "pyantz")

    assert JobConfig.model_validate({"function": NOP, "parameters": {}})
    with pytest.raises(ValidationError, match="not inside one of the modules"):
        JobConfig.model_validate({"function": "os.system", "parameters": {}})
