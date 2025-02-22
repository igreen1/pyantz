"""Test that the validate calls work"""
from pyantz.jobs.nop import nop
from pyantz.jobs.branch.explode_pipeline import explode_pipeline
import logging

from pydantic import ValidationError
import pytest

def test_validation_with_nop() -> None:
    """Test that bad parameters raise an error"""

    with pytest.raises(ValidationError):
        nop(
            [],
            logging.getLogger("test"),
        )
    with pytest.raises(ValidationError):
        nop(
            1,
            logging.getLogger("test"),
        )
    with pytest.raises(ValidationError):
        nop(
            1.0,
            logging.getLogger("test"),
        )
    with pytest.raises(ValidationError):
        nop(
            {"hello": {"there": "kenobi"}},
            logging.getLogger("test"),
        )
    with pytest.raises(ValidationError):
        nop(
            {"hello": {"type": "pipeline"}},
            logging.getLogger("test"),
        )
    with pytest.raises(ValidationError):
        nop(
            {},
            None
        )
    with pytest.raises(ValidationError):
        nop(
            {},
            []
        )
        

def test_validation_with_explode_pipeline() -> None:
    """Test that validation works on a submitter job (explode pipeline)"""

    test_pipeline_config = {
        'type': 'pipeline',
        'name': 'test_pipeline',
        'stages': [],
    }

    with pytest.raises(ValidationError):
        explode_pipeline(
            {
                'num_pipelines': 1,
                'pipeline_config_template': test_pipeline_config,
            },
            None,
            {},
            test_pipeline_config,
            logging.getLogger("test"),
            
        )
    with pytest.raises(ValidationError):
        explode_pipeline(
            {
                'num_pipelines': 1,
                'pipeline_config_template': test_pipeline_config,
            },
            lambda c: None,
            [],
            test_pipeline_config,
            logging.getLogger("test"),
            
        )
    with pytest.raises(ValidationError):
        explode_pipeline(
            {
                'num_pipelines': 1,
                'pipeline_config_template': test_pipeline_config,
            },
            lambda c: None,
            {},
            {"type": "job"},
            logging.getLogger("test"),
            
        )
    with pytest.raises(ValidationError):
        explode_pipeline(
            {
                'num_pipelines': 1,
                'pipeline_config_template': test_pipeline_config,
            },
            lambda c: None,
            {},
            test_pipeline_config,
            None
            
        )
    with pytest.raises(ValidationError):
        explode_pipeline(
            {
                'num_pipelines': 1,
                'pipeline_config_template': test_pipeline_config,
            },
            lambda c: None,
            {"test": {"type": "no"}},
            test_pipeline_config,
            logging.getLogger("test"),
            
        )