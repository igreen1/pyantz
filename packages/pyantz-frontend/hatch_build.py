"""Build the web ui (frontend/pyantz) into the package when it is built."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

SOURCE = Path("frontend") / "pyantz"
STATIC = Path("src") / "pyantz_frontend" / "static"


class FrontendBuildHook(BuildHookInterface):
    """Run ``npm run build`` and put the result in ``pyantz_frontend/static``.

    An sdist holds the result, not the sources of the ui, so a wheel made from
    an sdist uses it. An editable install builds nothing: use
    ``make frontend-bundle``.
    """

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        """Build the ui, unless this is an editable install or it is already built."""
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
        """Build the ui in `source` and copy it to `static`."""
        npm = shutil.which("npm")
        if npm is None:
            msg = "Building pyantz-frontend needs node and npm to build the web ui"
            raise RuntimeError(msg)
        if not (source / "node_modules").is_dir():
            subprocess.run([npm, "ci"], cwd=source, check=True)  # noqa: S603
        subprocess.run([npm, "run", "build"], cwd=source, check=True)  # noqa: S603
        shutil.rmtree(static, ignore_errors=True)
        shutil.copytree(source / "dist", static)
