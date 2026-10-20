"""Test the code base is formatted with ruff."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def test_code_is_formatted() -> None:
    """`ruff format --check` has nothing to change."""
    pytest.importorskip("ruff")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", str(ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_source_ends_with_newlines() -> None:
    """Every module in src ends with exactly one newline."""
    offenders = [
        path.name
        for path in (ROOT / "src").rglob("*.py")
        if path.stat().st_size and not path.read_text(encoding="utf-8").endswith("\n")
    ]

    assert not offenders
