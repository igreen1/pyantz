"""
All tasks have a status, this is the common enum
"""

from enum import IntEnum, auto


class Status(IntEnum):
    """The status of a task in antz"""

    ERROR = auto()
    SUCCESS = auto()
    FINAL = auto()
    READY = auto()
