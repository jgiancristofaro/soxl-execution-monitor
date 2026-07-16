import copy

import pytest

from pipeline.compute import compute_signals, validate_consistency


@pytest.fixture
def base_signals(soxx_df, soxl_df, manual, position, events):
    return compute_signals(
        soxx_df, soxl_df, upstream=None, manual=manual, position=position, events=events,
        generated_utc="2026-07-15T22:00:00+00:00",
    )


def test_golden_output_passes(base_signals):
    validate_consistency(base_signals)  # must not raise


def test_invariant1_act_mismatch_raises(base_signals):
    bad = copy.deepcopy(base_signals)
    bad["engine"]["act"] = not bad["engine"]["act"]
    with pytest.raises(ValueError, match="invariant 1"):
        validate_consistency(bad)


def test_invariant2_e_target_mismatch_raises(base_signals):
    bad = copy.deepcopy(base_signals)
    bad["engine"]["e_target"] = bad["engine"]["e_target"] + 0.05
    with pytest.raises(ValueError, match="invariant 2"):
        validate_consistency(bad)


def test_invariant3_deployed_mismatch_raises(base_signals):
    bad = copy.deepcopy(base_signals)
    bad["engine"]["deployed"] = bad["engine"]["deployed"] + 0.25
    with pytest.raises(ValueError, match="invariant 3"):
        validate_consistency(bad)


def test_invariant4_bad_gate_value_raises(base_signals):
    bad = copy.deepcopy(base_signals)
    bad["engine"]["gate"]["T"] = 0.75
    # keep e_target internally consistent with the bad T so invariant 2 doesn't fire first
    bad["engine"]["e_target"] = round(bad["engine"]["ensemble"] * 0.75, 3)
    with pytest.raises(ValueError, match="invariant 4"):
        validate_consistency(bad)


def test_invariant4_t_zero_without_streak_raises(base_signals):
    bad = copy.deepcopy(base_signals)
    bad["engine"]["gate"]["T"] = 0.0
    bad["engine"]["e_target"] = round(bad["engine"]["ensemble"] * 0.0, 3)
    bad["engine"]["gate"]["consec_below_ma200"] = 2
    bad["tripwires"]["ma200_break"] = True
    with pytest.raises(ValueError, match="invariant 4"):
        validate_consistency(bad)


def test_invariant5_series_length_mismatch_raises(base_signals):
    bad = copy.deepcopy(base_signals)
    bad["series"]["rv20"] = bad["series"]["rv20"][:-1]
    with pytest.raises(ValueError, match="invariant 5"):
        validate_consistency(bad)


def test_invariant6_sleeve_breach_without_alert_raises(base_signals):
    bad = copy.deepcopy(base_signals)
    bad["caps"]["sleeve_breach"] = True
    bad["alerts"] = []
    with pytest.raises(ValueError, match="invariant 6"):
        validate_consistency(bad)


def test_invariant6_sleeve_breach_with_alert_passes(base_signals):
    bad = copy.deepcopy(base_signals)
    bad["caps"]["sleeve_breach"] = True
    bad["alerts"] = [{"type": "cap_breach", "title": "x", "body": "y"}]
    validate_consistency(bad)  # must not raise
