"""Test the source has no common misspellings."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SOURCE = Path(__file__).parent.parent / "src"

# typos which were in the code, spelled out so they don't come back
PAST_TYPOS = (
    "lcoal",
    "fucntion",
    "re2quirements",
    "POssible",
    "SOmething",
    "submti",
    "depenedencies",
    "serialiation",
    "actuaally",
    "responsbilities",
    "conveience",
    "unlikley",
    "Parmeters",
    "updateing",
    "Reformate",
    "reuslt",
    "paramters",
)


def test_past_typos_have_not_returned() -> None:
    """None of the typos found in an audit appear in the source."""
    found = [
        f"{path.name}: {typo}"
        for path in SOURCE.rglob("*.py")
        for typo in PAST_TYPOS
        if typo in path.read_text(encoding="utf-8")
    ]

    assert found == []


@pytest.mark.skipif(shutil.which("codespell") is None, reason="codespell not installed")
def test_codespell_is_happy() -> None:
    """`codespell src` reports nothing."""
    result = subprocess.run(
        ["codespell", str(SOURCE)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout
