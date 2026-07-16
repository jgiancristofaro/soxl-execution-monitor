import pytest

from pipeline.compute import compute_signals


@pytest.fixture
def signals(soxx_df, soxl_df, manual, position, events):
    return compute_signals(
        soxx_df, soxl_df, upstream=None, manual=manual, position=position, events=events,
        generated_utc="2026-07-15T22:00:00+00:00",
    )


def test_golden_values_within_tolerance(signals, golden):
    e = signals["engine"]
    assert e["rv20"] == pytest.approx(golden["rv20"], abs=0.005)
    assert e["rv20_p90"] == pytest.approx(golden["rv20_p90"], abs=0.005)
    for r in ("R1", "R2", "R3", "R4"):
        assert e["rules"][r] == pytest.approx(golden["rules"][r], abs=0.01)
    assert e["ensemble"] == pytest.approx(golden["ensemble"], abs=0.01)
    assert e["gate"]["T"] == golden["T"]
    assert e["e_target"] == pytest.approx(0.632, abs=0.01)
    assert e["e_target"] == golden["e_target"]


def test_act_true(signals):
    assert signals["engine"]["act"] is True


def test_t2_waiting(signals):
    t2 = next(t for t in signals["tranches"] if t["id"] == "T2")
    assert t2["status"] == "WAITING"


def test_vrp_zone_buy_optionality(signals):
    assert signals["vrp"]["zone"] == "BUY_OPTIONALITY"


def test_no_tripwires(signals):
    assert signals["tripwires"]["any"] is False


def test_schema_valid(signals):
    import json
    import pathlib

    import jsonschema

    schema = json.loads(
        (pathlib.Path(__file__).parent / "fixtures" / "schema.json").read_text()
    )
    jsonschema.validate(signals, schema)
