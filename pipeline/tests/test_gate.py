import pandas as pd

from pipeline.engine import trend_gate


def _series(closes, ma200):
    idx = pd.date_range("2026-01-01", periods=len(closes))
    return pd.Series(closes, index=idx), pd.Series(ma200, index=idx)


def test_all_above_gate_open():
    closes, ma200 = _series([110, 111, 112], [100, 100, 100])
    T, consec = trend_gate(closes, ma200)
    assert T == 1.0
    assert consec == 0


def test_one_close_below_half_gate():
    closes, ma200 = _series([110, 111, 90], [100, 100, 100])
    T, consec = trend_gate(closes, ma200)
    assert T == 0.5
    assert consec == 1


def test_five_consecutive_below_closes_gate_and_sticky():
    closes, ma200 = _series([90, 89, 88, 87, 86], [100] * 5)
    T, consec = trend_gate(closes, ma200)
    assert T == 0.0
    assert consec == 5

    closes6, ma2006 = _series([90, 89, 88, 87, 86, 85], [100] * 6)
    T6, consec6 = trend_gate(closes6, ma2006)
    assert T6 == 0.0
    assert consec6 == 6


def test_four_below_then_one_above_resets():
    closes, ma200 = _series([90, 89, 88, 87, 105], [100] * 5)
    T, consec = trend_gate(closes, ma200)
    assert T == 1.0
    assert consec == 0


def test_equal_to_ma200_counts_as_below():
    closes, ma200 = _series([110, 100], [100, 100])
    T, consec = trend_gate(closes, ma200)
    assert T == 0.5
    assert consec == 1
