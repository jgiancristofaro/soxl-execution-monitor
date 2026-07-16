import pytest

from pipeline.engine import ensemble, sizing_rules


def test_high_vol_reference_case():
    rules = sizing_rules(rv20=0.712, rv20_p90=0.621)
    assert rules["R1"] == pytest.approx(0.5618, abs=0.0005)
    assert rules["R2"] == pytest.approx(0.7022, abs=0.0005)
    assert rules["R3"] == pytest.approx(0.7022, abs=0.0005)
    assert rules["R4"] == pytest.approx(0.5618, abs=0.0005)
    assert ensemble(rules) == pytest.approx(0.632, abs=0.001)


def test_low_vol_full_exposure():
    rules = sizing_rules(rv20=0.50, rv20_p90=0.62)
    assert rules["R1"] == 1.0
    assert rules["R2"] == 1.0
    assert rules["R3"] == 1.0  # 0.50 <= 0.60
    assert rules["R4"] == 1.0  # 0.50 <= 0.55
    assert ensemble(rules) == 1.0


def test_r4_fixed_threshold_deleverage():
    rules = sizing_rules(rv20=0.58, rv20_p90=0.90)
    assert rules["R4"] == pytest.approx(0.40 / 0.58, abs=1e-6)
    assert rules["R3"] == 1.0  # 0.58 <= 0.60


def test_very_low_vol_all_full():
    rules = sizing_rules(rv20=0.30, rv20_p90=0.90)
    assert all(v == 1.0 for v in rules.values())


def test_extreme_vol_p90_gated():
    rules = sizing_rules(rv20=2.0, rv20_p90=0.5)
    assert rules["R1"] == pytest.approx(0.20, abs=1e-6)
    assert rules["R2"] == pytest.approx(0.25, abs=1e-6)
