import pytest

from pipeline.engine import vrp_zone


def test_buy_optionality_zone():
    result = vrp_zone(0.46, "2026-07-01", rv20=0.712, last_session="2026-07-15")
    assert result["vrp"] == pytest.approx(-0.252, abs=0.001)
    assert result["zone"] == "BUY_OPTIONALITY"


def test_derisk_shares_zone():
    result = vrp_zone(0.80, "2026-07-14", rv20=0.60, last_session="2026-07-15")
    assert result["vrp"] == pytest.approx(0.20, abs=0.001)
    assert result["zone"] == "DERISK_SHARES"


def test_neutral_zone():
    result = vrp_zone(0.55, "2026-07-14", rv20=0.60, last_session="2026-07-15")
    assert result["zone"] == "NEUTRAL"


def test_missing_iv30_returns_none_zone_and_stale():
    result = vrp_zone(None, None, rv20=0.60, last_session="2026-07-15")
    assert result["zone"] is None
    assert result["stale"] is True


def test_stale_iv_still_computes_zone():
    # 10 business days before 2026-07-15
    result = vrp_zone(0.46, "2026-07-01", rv20=0.712, last_session="2026-07-15")
    assert result["stale"] is True
    assert result["zone"] == "BUY_OPTIONALITY"
