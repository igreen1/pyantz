"""Create a file and optionally add text."""

from pathlib import Path

from pydantic import BaseModel

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class CreateFileParams(BaseModel):
    """Required inputs to create a file."""

    # path to the file to create
    path: Path

    # optionally, write the text contents to file
    contents: str | None = None

    # if set to true, overwrites the contents of the file
    # if contents is empty and overwrite is true, clears it
    overwrite: bool = True


@add_parameters(CreateFileParams)
@no_submit_fn
def create(params: CreateFileParams) -> bool:
    """Create the file as requested and write contents if provided."""
    if params.overwrite:
        params.path.unlink(missing_ok=True)
    params.path.touch(exist_ok=True)

    if params.contents:
        params.path.write_text(params.contents, encoding="utf-8")

    return True
