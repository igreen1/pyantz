"""Touch/create a file."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from pyantz.infrastructure.config import add_parameters, no_submit_fn


class TouchFileParameters(BaseModel):
    """Touch a file (create it)."""

    path: Path
    """Path to the file to create."""

    exist_ok: bool = True
    """If False, the job fails when the file already exists (see
    :meth:`pathlib.Path.touch`)."""


@add_parameters(TouchFileParameters)
@no_submit_fn
def touch_file(params: TouchFileParameters) -> bool:
    """Touch a file (create it with no values).

    Mostly used for testing. An existing file keeps its contents and only has its
    modification time updated.

    Args:
        params: the job's parameters, validated as :class:`TouchFileParameters`.

    Parameters:
        path (Path): path to the file to create.
        exist_ok (bool): if False, the job fails when the file already exists.
            Defaults to True.

    Returns:
        bool: True if the file was touched, False if it already existed and
        ``exist_ok`` is False.

    Raises:
        OSError: if the file can't be created, e.g., its directory doesn't exist.

    Example:
        .. testsetup:: testing-touch

            import os, shutil, tempfile
            start_dir = os.getcwd()
            os.chdir(tempfile.mkdtemp())

        .. testcode:: testing-touch

            from pyantz.jobs.testing.touch_file import touch_file

            # a registered job is called with its parameters and a submit function
            def submit(job):
                pass

            print(touch_file({"path": "touched.txt"}, submit))
            print(touch_file({"path": "touched.txt", "exist_ok": False}, submit))

        .. testoutput:: testing-touch

            True
            False

        .. testcleanup:: testing-touch

            tmp = os.getcwd()
            os.chdir(start_dir)
            shutil.rmtree(tmp)

    """
    try:
        params.path.touch(exist_ok=params.exist_ok)
    except FileExistsError:
        return False
    return True
