"""Delete a file or directory."""

from pydantic import BaseModel, DirectoryPath, FilePath

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class DeleteParams(BaseModel):
    """Parameters to define what to delete."""

    # location to delete
    path: FilePath | DirectoryPath

    missing_ok: bool = True


@add_parameters(DeleteParams)
@no_submit_fn
def delete(params: DeleteParams) -> bool:
    """Delete the file passed in delete params."""
    if not params.path.exists():
        return params.missing_ok

    if params.path.is_file():
        params.path.unlink()
    else:
        params.path.rmdir()

    return True
