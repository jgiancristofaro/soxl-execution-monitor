import pytest

from pipeline.engine import churn


def test_large_gap_acts():
    gap, act = churn(0.632, 0.0)
    assert gap == pytest.approx(0.632)
    assert act is True


def test_small_gap_holds():
    gap, act = churn(0.09, 0.0)
    assert gap == pytest.approx(0.09)
    assert act is False


def test_boundary_exactly_band_acts():
    gap, act = churn(0.10, 0.0)
    assert gap == pytest.approx(0.10)
    assert act is True


def test_over_deployed_negative_gap_acts():
    gap, act = churn(0.0, 0.10)
    assert gap == pytest.approx(-0.10)
    assert act is True
