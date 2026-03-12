"""Touch/create a file."""


from typing import TYPE_CHECKING

from pydantic import BaseModel

from pyantz.infrastructure.config import add_parameters, no_submit_fn

if TYPE_CHECKING:
    from pathlib import Path


class TouchFileParameters(BaseModel):
    """Touch a file (create it)."""

    # path to the file to create
    path: Path

    # see pathlib.Path.touch docs
    exist_ok: bool = True


@add_parameters(TouchFileParameters)
@no_submit_fn
def touch_file(params: TouchFileParameters) -> bool:
    """Touch a file (create it with no values).

    Mostly used for testing.
    """
    try:
        params.path.touch(exist_ok=params.exist_ok)
    except FileExistsError:
        return False
    return True
