"""https://slurm.schedmd.com/rest_api.html#v0.0.42_wckey_tag_struct"""

from pydantic import BaseModel


class WckeyTagStruct(BaseModel):
    """v0.0.42 WCKEY_TAG_STRUCT"""

    wckey: str
    flags: list[str]
