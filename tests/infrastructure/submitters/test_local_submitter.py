"""Test that the local submitter runner works"""

import os

import pyantz.run


def test_local_submitter(tmpdir) -> None:
    dst_file = os.path.join(tmpdir, "end.txt")

    src_file = os.path.join(tmpdir, "start.txt")

    test_text: str = "Hello there general kenobi"

    with open(src_file, "w", encoding='utf-8') as fh:
        fh.write(test_text)

    test_config = {
        "submitter_config": {"type": "local"},
        "analysis_config": {
            "variables": {},
            "config": {
                "type": "pipeline",
                "stages": [
                    {
                        "type": "job",
                        "function": "antz.jobs.copy.copy",
                        "parameters": {
                            "source": os.fspath(src_file),
                            "destination": os.fspath(dst_file),
                        },
                    }
                ],
            },
        },
    }

    antz.run.run(test_config)

    assert os.path.exists(dst_file)
    with open(dst_file, "r", encoding='utf-8') as fh:
        ret = fh.read()
    assert ret == test_text
