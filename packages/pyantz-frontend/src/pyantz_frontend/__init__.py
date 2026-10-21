"""The built web ui of pyantz, which `pyantz-frontend` serves."""

from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"
"""The directory with the built ui (an ``index.html`` and its assets)."""
