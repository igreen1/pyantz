"""Build the web ui (frontend/pyantz) into the package when it is built."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

# hatchling is only installed in the build environment, not the development one
from hatchling.builders.hooks.plugin.interface import (  # ty: ignore[unresolved-import]
    BuildHookInterface,
)

SOURCE = Path("frontend") / "pyantz"
"""Sources of the web ui, relative to the repository's root."""

STATIC = Path("src") / "pyantz_frontend" / "static"
"""Where the built ui goes, relative to this package's root."""


class FrontendBuildHook(BuildHookInterface):
    """Run ``npm run build`` and put the result in ``pyantz_frontend/static``.

    An sdist holds the result, not the sources of the ui, so a wheel made from
    an sdist uses it. An editable install builds nothing: use
    ``make frontend-bundle``.
    """

    PLUGIN_NAME = "custom"
    """Name of the hook, as hatch refers to it."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        """Build the ui, unless this is an editable install or it is already built.

        Without the ui's sources (e.g., building a wheel from an sdist), the ui
        built into the sdist is used.

        Args:
            version: the kind of build, e.g., ``standard`` or ``editable``.
            build_data: hatch's data about the build (unused).

        Returns:
            None.

        Raises:
            FileNotFoundError: if there are neither sources nor a built ui.
            RuntimeError: if npm isn't installed.
            subprocess.CalledProcessError: if npm fails.

        """
        root = Path(self.root)
        static = root / STATIC
        source = root.parent.parent / SOURCE
        if version == "editable":
            return
        if not (source / "package.json").is_file():
            if not (static / "index.html").is_file():
                msg = f"Cannot build the web ui: there is no {source} and no {static}"
                raise FileNotFoundError(msg)
            return
        self._build(source, static)

    def _build(self, source: Path, static: Path) -> None:
        """Build the ui in `source` and copy it to `static`.

        Runs ``npm ci`` first if the dependencies aren't installed.

        Args:
            source: the ui's sources (``frontend/pyantz``).
            static: where to put the built ui; replaced if it exists.

        Returns:
            None.

        Raises:
            RuntimeError: if npm isn't installed.
            subprocess.CalledProcessError: if npm fails.

        """
        npm = shutil.which("npm")
        if npm is None:
            msg = "Building pyantz-frontend needs node and npm to build the web ui"
            raise RuntimeError(msg)
        if not (source / "node_modules").is_dir():
            subprocess.run([npm, "ci"], cwd=source, check=True)  # noqa: S603
        subprocess.run([npm, "run", "build"], cwd=source, check=True)  # noqa: S603
        shutil.rmtree(static, ignore_errors=True)
        shutil.copytree(source / "dist", static)
