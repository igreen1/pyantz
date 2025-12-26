"""Basic jobs for testing."""

from .nop import do_nothing
from .touch_file import touch_file

__all__ = [
    "do_nothing",
    "touch_file",
]
