"""Versioned *dynamic article* specification: do not silently rewrite v0.1 results."""
from .core import REQUIREMENTS
from .dynamics import DynamicsConfig
from .verification_v05 import EXTRA_REQUIREMENTS, ALL_TESTS

ARTICLE_ID = 'SATVV-DYNAMIC-TOY-06'
SPECIFICATION = {**REQUIREMENTS, **EXTRA_REQUIREMENTS}
SPECIFICATION['REQ-EPS-I'] = 'Loaded EPS current <= 1.30 A for the dynamic simulated article'


def validate_dynamic_specification() -> None:
    config = DynamicsConfig()
    assert config.max_bus_current_a == 1.30
    absent = {rid for test in ALL_TESTS for rid in test.checks if rid not in SPECIFICATION}
    if absent:
        raise AssertionError('Unmapped dynamic requirement(s): '+str(absent))
