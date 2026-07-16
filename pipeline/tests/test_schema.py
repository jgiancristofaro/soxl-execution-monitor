import copy
import json
import pathlib

import jsonschema
import pytest

from pipeline.compute import compute_signals

SCHEMA_PATH = pathlib.Path(__file__).parent / "fixtures" / "schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture
def signals(soxx_df, soxl_df, manual, position, events):
    return compute_signals(
        soxx_df, soxl_df, upstream=None, manual=manual, position=position, events=events,
        generated_utc="2026-07-15T22:00:00+00:00",
    )


def test_golden_output_validates(signals, schema):
    jsonschema.validate(signals, schema)


def test_missing_required_field_fails(signals, schema):
    mutated = copy.deepcopy(signals)
    del mutated["engine"]["e_target"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(mutated, schema)
