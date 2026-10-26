"""Test running commands with dispatch."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from pyantz.jobs.subproc.dispatch import DispatchParams, dispatch

if TYPE_CHECKING:
    from pathlib import Path


def _dispatch(code: str, **parameters: Any) -> bool:  # noqa: ANN401
    params = DispatchParams(cmd=(sys.executable, "-c", code), **parameters)
    return dispatch(params.model_dump(), lambda *_: None)


def test_environment_reaches_the_command(tmp_path: Path) -> None:
    """Variables from `env` are visible to the child."""
    out = tmp_path / "out.txt"

    assert _dispatch(
        "import os; print(os.environ['PYANTZ_TEST_VALUE'])",
        env={"PYANTZ_TEST_VALUE": "visible"},
        stdout_file=out,
    )

    assert out.read_text().strip() == "visible"


def test_failing_command_still_saves_its_output(tmp_path: Path) -> None:
    """Output is exactly what's needed to debug a failure, so it is kept."""
    out, err = tmp_path / "out.txt", tmp_path / "err.txt"

    assert not _dispatch(
        "import sys; print('so'); print('boom', file=sys.stderr); sys.exit(3)",
        stdout_file=out,
        stderr_file=err,
    )

    assert out.read_text().strip() == "so"
    assert err.read_text().strip() == "boom"


def test_timeout_saves_partial_output(tmp_path: Path) -> None:
    """A command that times out has its output so far saved, and the job fails."""
    out = tmp_path / "out.txt"

    assert not _dispatch(
        "import sys, time; print('started', flush=True); time.sleep(30)",
        timeout=1,
        stdout_file=out,
    )

    assert out.exists()


def test_stderr_directory_is_created(tmp_path: Path) -> None:
    """Both output files get their parent directories."""
    err = tmp_path / "a" / "b" / "err.txt"

    assert _dispatch("import sys; print('x', file=sys.stderr)", stderr_file=err)

    assert err.read_text().strip() == "x"


def test_separate_files_are_overwritten_not_appended(tmp_path: Path) -> None:
    """Different stdout and stderr files don't accumulate output across runs."""
    out, err = tmp_path / "out.txt", tmp_path / "err.txt"
    code = "import sys; print('o'); print('e', file=sys.stderr)"

    assert _dispatch(code, stdout_file=out, stderr_file=err)
    assert _dispatch(code, stdout_file=out, stderr_file=err)

    assert out.read_text() == "o\n"
    assert err.read_text() == "e\n"


def test_same_file_gets_both_with_a_header(tmp_path: Path) -> None:
    """With one file for both, stdout comes first, then a header, then stderr."""
    both = tmp_path / "both.txt"

    assert _dispatch(
        "import sys; print('o'); print('e', file=sys.stderr)",
        stdout_file=both,
        stderr_file=both,
    )

    assert both.read_text() == "o\n\n--- stderr ---\ne\n"


def test_missing_command_fails_cleanly() -> None:
    """A command which does not exist is a failed job, not an exception."""
    params = DispatchParams(cmd=("definitely-not-a-command-xyz",))

    assert dispatch(params.model_dump(), lambda *_: None) is False
