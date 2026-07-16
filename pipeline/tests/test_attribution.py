import pytest

from pipeline.engine import _accumulate, attribution


def test_next_close_accounting_with_slippage_on_change_day():
    """3-day synthetic per §3.10: strict next-close fills, 10bps slippage on the day a
    position change is set. Values pinned after implementing to spec (not hand-derived
    from the spec's illustrative prose, which was approximate)."""
    equity, bh = _accumulate(positions=[1.0, 0.5, 0.5], rets=[0.10, -0.10, 0.10])

    assert equity[0] == pytest.approx(1.10)          # no prior position -> no slippage
    assert equity[1] == pytest.approx(1.04445)        # 1.0->0.5 switch charged 10bps*0.5
    assert equity[2] == pytest.approx(1.0966725)      # no change day 3 -> no slippage

    assert bh == [pytest.approx(v) for v in (1.10, 0.99, 1.089)]


def test_no_position_change_charges_no_slippage():
    equity, _ = _accumulate(positions=[0.5, 0.5, 0.5], rets=[0.01, 0.01, 0.01])
    expected = 1.0
    for r in (0.01, 0.01, 0.01):
        expected *= (1 + 0.5 * r)
    assert equity[-1] == pytest.approx(expected)


def test_attribution_output_shape_on_fixtures(soxx_df, soxl_df):
    result = attribution(soxx_df, soxl_df)
    assert len(result["dates"]) == len(result["equity_engine"]) == len(result["equity_bh"])
    assert result["equity_engine"], "expected non-empty backtest window from BACKTEST_START"
    assert result["dates"][0] >= "2026-01-20"
