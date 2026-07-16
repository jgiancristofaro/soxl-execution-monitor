import pytest

from pipeline.engine import caps


def _position(tranches):
    return {"tranches": tranches}


def test_tranche_boundary_inclusive_breach():
    position = _position([
        {"id": "T1", "status": "DEPLOYED", "pct": 0.25, "cost_basis_soxl": 200.0, "fill_date": "2026-01-01"},
    ])
    result = caps(position, soxl_close=150.0)
    assert result["tranche_breaches"] == ["T1"]


def test_tranche_just_inside_cap_is_ok():
    position = _position([
        {"id": "T1", "status": "DEPLOYED", "pct": 0.25, "cost_basis_soxl": 200.0, "fill_date": "2026-01-01"},
    ])
    result = caps(position, soxl_close=151.0)
    assert result["tranche_breaches"] == []


def test_blended_sleeve_breach():
    position = _position([
        {"id": "T1", "status": "DEPLOYED", "pct": 0.25, "cost_basis_soxl": 200.0, "fill_date": "2026-01-01"},
        {"id": "T2", "status": "DEPLOYED", "pct": 0.20, "cost_basis_soxl": 180.0, "fill_date": "2026-01-05"},
    ])
    result = caps(position, soxl_close=120.0)
    # weighted average of (0.25 @ ret -0.40) and (0.20 @ ret -0.33333), normalized to the
    # 0.45 deployed sleeve fraction (not total C) -- see caps() docstring rationale.
    assert result["sleeve_pnl"] == pytest.approx(-0.370370, abs=1e-5)
    assert result["sleeve_breach"] is True


def test_null_cost_basis_no_crash_no_cap_evaluated():
    position = _position([
        {"id": "T1", "status": "WAITING", "pct": 0.25, "cost_basis_soxl": None, "fill_date": None},
        {"id": "T2", "status": "WAITING", "pct": 0.20, "cost_basis_soxl": None, "fill_date": None},
    ])
    result = caps(position, soxl_close=120.0)
    assert result["tranche_breaches"] == []
    assert result["sleeve_pnl"] is None
    assert result["sleeve_breach"] is False
