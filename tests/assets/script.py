#!/usr/bin/env python3
"""Script run by the large pipeline tests: writes a small csv to the given path."""

from __future__ import annotations

import sys
from pathlib import Path

Path(sys.argv[1]).write_text("a,b,c\n1,2,3\n", encoding="utf-8")
