"""Tests editing json files."""

import json
import logging
import math
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pydantic import ValidationError

import pyantz.jobs.file.edit_json as edit_json_mod
from pyantz.infrastructure.config.base import JobConfig, PipelineConfig
from pyantz.infrastructure.core.pipeline import run_pipeline
from pyantz.infrastructure.core.status import Status

_json_key_strategy = st.from_regex(r"[^\.]+", fullmatch=True)
_json_value_strategy = st.one_of(
    st.integers(),
    st.floats(),
    st.booleans(),
    st.none(),
    st.lists(
        st.one_of(
            st.integers(),
            st.floats(),
            st.booleans(),
            st.none(),
        )
    ),
)
_json_like_strategy = st.dictionaries(_json_key_strategy, _json_value_strategy)


def nested_dictionaries():
    leaf_values = _json_value_strategy
    return st.recursive(
        st.dictionaries(_json_key_strategy, leaf_values),
        lambda children: st.dictionaries(_json_key_strategy, children),
        max_leaves=3,
    )


@given(
    _json_like_strategy,
    _json_key_strategy,
    _json_value_strategy,
)
def test_edit_simple_json(data: dict[str, Any], key, value) -> None:
    """Test editing a simple single-level json file."""
    assume("." not in key)
    expected = deepcopy(data)
    expected[key] = value

    assert edit_json_mod.nested_edit(data, key, value) == expected


@given(
    st.dictionaries(st.text(), _json_like_strategy),
    _json_key_strategy,
    _json_key_strategy,
    _json_value_strategy,
)
def test_nested_dictionary_2_level(data: dict[str, dict[str, Any]], key1, key2, value) -> None:
    assume("." not in key1 and "." not in key2)

    expected = deepcopy(data)
    if key1 not in expected:
        expected[key1] = {}
    expected[key1][key2] = value

    assert edit_json_mod.nested_edit(data, f"{key1}.{key2}", value) == expected


@given(
    nested_dictionaries(),
    st.lists(_json_key_strategy, min_size=1),
    _json_value_strategy,
)
def test_nested_dictionary_n_level(data: dict[str, Any], keys: list[str], value: Any) -> None:
    """Test a dictionary with an arbitrary number of dictionaries nested."""
    assume(all("." not in key for key in keys))

    result = edit_json_mod.nested_edit(data, ".".join(keys), value)

    curr = result
    for key in keys:
        assert key in curr
        curr = curr[key]

    if value is None:
        assert curr is None
    elif isinstance(value, float) and math.isnan(value):
        assert math.isnan(curr)
    else:
        assert curr == value


def test_edit_json_job(tmpdir: Path) -> None:
    """Test running the job in a pipeline."""
    json_path = os.path.join(tmpdir, "json_file.json")

    given_json = {
        "field1": {"field2": None},
        "field3": {
            "hello": "there",
        },
        "field2": [1, 2, 3, 3],
    }

    with open(json_path, "w") as fh:
        json.dump(given_json, fh)

    expected_json = {
        "field1": {"field2": {"field3": None}},
        "field3": {
            "hello": "there",
        },
        "field2": [1, 2, 3, 3],
    }

    job_config = JobConfig.model_validate(
        {
            "type": "job",
            "function": "pyantz.jobs.file.edit_json.edit_json",
            "parameters": {
                "path": "%{my_path}",
                "field": "field1.field2.field3",
                "value": None,
            },
        }
    )
    pipeline_config = PipelineConfig.model_validate({"type": "pipeline", "stages": [job_config]})

    def submit_fn(config) -> None:
        msg = "Submit fn shouldn't be called"
        raise RuntimeError(msg)

    assert (
        run_pipeline(
            pipeline_config,
            {"my_path": os.fspath(json_path)},
            submit_fn,
            logging.getLogger("test"),
        )
        == Status.SUCCESS
    )

    with open(json_path) as fh:
        returned_val = json.load(fh)

    assert expected_json == returned_val


def test_nonexistent_json_errors_with_variable_path() -> None:
    """Test that files which don't exist raise errors."""
    json_path = "some/random/path/doesnt/exist"

    job_config = JobConfig.model_validate(
        {
            "type": "job",
            "function": "pyantz.jobs.file.edit_json.edit_json",
            "parameters": {
                "path": "%{my_path}",
                "field": "field1.field2.field3",
                "value": None,
            },
        }
    )
    pipeline_config = PipelineConfig.model_validate({"type": "pipeline", "stages": [job_config]})

    def submit_fn(config) -> None:
        msg = "Submit fn shouldn't be called"
        raise RuntimeError(msg)

    assert (
        run_pipeline(
            pipeline_config,
            {"my_path": os.fspath(json_path)},
            submit_fn,
            logging.getLogger("test"),
        )
        == Status.ERROR
    )

    assert not os.path.exists(json_path)


def test_nonexistent_json_errors_with_static_path() -> None:
    """Test that files which don't exist raise errors."""
    json_path = "some/random/path/doesnt/exist"

    with pytest.raises(ValidationError):
        JobConfig.model_validate(
            {
                "type": "job",
                "function": "pyantz.jobs.file.edit_json.edit_json",
                "parameters": {
                    "path": os.fspath(json_path),
                    "field": "field1.field2.field3",
                    "value": None,
                },
            }
        )
