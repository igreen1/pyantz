"""Test that importing the jobs package registers every job."""

from __future__ import annotations

import subprocess
import sys


def _run(code: str) -> subprocess.CompletedProcess[str]:
    """Run python code in a fresh interpreter (the registry is global)."""
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )


def test_importing_jobs_has_no_circular_import_error() -> None:
    """`import pyantz.jobs` works in a fresh interpreter."""
    result = _run("import pyantz.jobs")

    assert result.returncode == 0, result.stderr


def test_wrapper_jobs_are_registered() -> None:
    """The loop and submit wrappers are registered by `import pyantz.jobs`."""
    result = _run(
        "import pyantz.jobs\n"
        "from pyantz.infrastructure.config.parameters.decorators import "
        "get_registered_functions\n"
        "print('\\n'.join(fn.PYANTZ_NAME for fn in get_registered_functions()))\n",
    )

    assert result.returncode == 0, result.stderr
    names = set(result.stdout.split())
    assert "pyantz.jobs.wrappers.loops.local_for_loop" in names
    assert "pyantz.jobs.wrappers.submit.submit" in names
    assert "pyantz.jobs.wrappers.submit.new_host" in names


def test_importing_jobs_before_the_top_level_package_works() -> None:
    """Importing the submodule directly (as the api does) is also fine."""
    result = _run("import pyantz.jobs.wrappers.submit")

    assert result.returncode == 0, result.stderr


def test_every_wrapper_module_is_imported_by_the_package() -> None:
    """No module of `pyantz.jobs.wrappers` is missing from the package imports."""
    import pkgutil  # noqa: PLC0415

    from pyantz.jobs import wrappers  # noqa: PLC0415

    modules = {info.name for info in pkgutil.iter_modules(wrappers.__path__)}

    assert modules == set(wrappers.__all__)
