"""Reconciled Plan v1.0 — pure sizing/gating/tranche/cap/vrp/attribution functions.

No I/O. No reference to the upstream soxx-regime-monitor feed (display only, C2) —
enforced by pipeline/tests/test_isolation.py.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

# ── Reconciled Plan v1.0 constants — the ONLY place numbers live ──────────
RULES = (
    ("R1", "p90", 0.40),   # (name, trigger: "p90" | fixed float, vol budget)
    ("R2", "p90", 0.50),
    ("R3", 0.60,  0.50),
    ("R4", 0.55,  0.40),
)
P90_WINDOW       = 252
P90_MIN_PERIODS  = 120
GATE_HALF        = 0.5     # T on any close <= MA200
GATE_ZERO_DAYS   = 5       # consecutive closes <= MA200 -> T = 0.0
CHURN_BAND       = 0.10    # |gap| >= band -> ACT
T2_RV_TRIGGER    = 0.65
T2_ID20_TRIGGER  = -0.03
CAP_TRANCHE      = -0.25
CAP_SLEEVE       = -0.35
VRP_BUY_ZONE     = -0.10
VRP_SELL_ZONE    = +0.10
IV_STALE_SESS    = 7
SLIPPAGE_BPS     = 10      # attribution backtest, per switch
BACKTEST_START   = "2026-01-20"
EVENT_NOADD_H    = 24


def sizing_rules(rv20: float, rv20_p90: float) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, trigger, budget in RULES:
        threshold = rv20_p90 if trigger == "p90" else trigger
        out[name] = 1.0 if rv20 <= threshold else min(1.0, budget / rv20)
    return out


def ensemble(rules: dict[str, float]) -> float:
    return sum(rules.values()) / len(rules)


def trend_gate(closes: pd.Series, ma200: pd.Series) -> tuple[float, int]:
    """Trailing consecutive closes <= ma200, ending at the last row -> (T, consec_below)."""
    below = (closes <= ma200)
    consec = 0
    for is_below in reversed(below.tolist()):
        if is_below:
            consec += 1
        else:
            break
    if consec >= GATE_ZERO_DAYS:
        T = 0.0
    elif consec >= 1:
        T = GATE_HALF
    else:
        T = 1.0
    return T, consec


def e_target(ens: float, T: float) -> float:
    return round(ens * T, 3)


def churn(e_tgt: float, deployed: float) -> tuple[float, bool]:
    gap = e_tgt - deployed
    act = abs(gap) >= CHURN_BAND - 1e-9
    return gap, act


def tranche_states(
    position: dict,
    rv20: float,
    id20: float,
    manual: dict,
    tripped: bool,
    T: float,
) -> list[dict]:
    pos_by_id = {t["id"]: t for t in position["tranches"]}
    out: list[dict] = []

    t1 = pos_by_id["T1"]
    if t1["status"] == "DEPLOYED":
        out.append({"id": "T1", "status": "DEPLOYED", "pct": t1["pct"], "triggers": []})
    else:
        out.append({
            "id": "T1", "status": "WAITING", "pct": t1["pct"],
            "triggers": [{"name": "event-branch discretion (TSMC print)", "pass": False}],
        })

    t2 = pos_by_id["T2"]
    rv_pass = rv20 < T2_RV_TRIGGER
    id_pass = id20 > T2_ID20_TRIGGER
    t2_triggers = [
        {"name": f"rv20 < {T2_RV_TRIGGER}", "pass": rv_pass},
        {"name": f"id20 > {T2_ID20_TRIGGER}", "pass": id_pass},
    ]
    if t2["status"] == "DEPLOYED":
        t2_status = "DEPLOYED"
    elif rv_pass or id_pass:
        t2_status = "ARMED"
    else:
        t2_status = "WAITING"
    out.append({"id": "T2", "status": t2_status, "pct": t2["pct"], "triggers": t2_triggers})

    t3 = pos_by_id["T3"]
    gauntlet = bool(manual.get("gauntlet_cleared", False))
    t3_triggers = [
        {"name": "gauntlet_cleared", "pass": gauntlet},
        {"name": "trend gate T >= 0.5", "pass": T >= GATE_HALF},
        {"name": "no tripwire tripped", "pass": not tripped},
    ]
    if t3["status"] == "DEPLOYED":
        t3_status = "DEPLOYED"
    elif gauntlet and T >= GATE_HALF and not tripped:
        t3_status = "ARMED"
    else:
        t3_status = "WAITING"
    out.append({"id": "T3", "status": t3_status, "pct": t3["pct"], "triggers": t3_triggers})

    return out


def caps(position: dict, soxl_close: float) -> dict:
    tranche_breaches: list[str] = []
    tranche_pnls: dict[str, float | None] = {}
    weighted_sum = 0.0
    weight_total = 0.0

    for t in position["tranches"]:
        cb = t.get("cost_basis_soxl")
        if t["status"] != "DEPLOYED" or cb is None:
            tranche_pnls[t["id"]] = None
            continue
        pnl = soxl_close / cb - 1.0
        tranche_pnls[t["id"]] = round(pnl, 6)
        if pnl <= CAP_TRANCHE:
            tranche_breaches.append(t["id"])
        pct = t["pct"] or 0.0
        weighted_sum += pct * pnl
        weight_total += pct

    # "Blended" = weighted average return of capital actually deployed (weights normalized
    # to the deployed sleeve, not to total C) — an unweighted sum would understate drawdown
    # once only part of C is committed and never trip the sleeve cap.
    sleeve_pnl = round(weighted_sum / weight_total, 6) if weight_total > 0 else None
    sleeve_breach = sleeve_pnl is not None and sleeve_pnl <= CAP_SLEEVE

    return {
        "tranche_breaches": tranche_breaches,
        "tranche_pnls": tranche_pnls,
        "sleeve_pnl": sleeve_pnl,
        "sleeve_breach": sleeve_breach,
    }


def vrp_zone(iv30: float | None, iv30_asof: str | None, rv20: float, last_session: str) -> dict:
    if iv30 is None or iv30_asof is None:
        return {"iv30": None, "iv30_asof": iv30_asof, "stale": True, "vrp": None, "zone": None}

    vrp = round(iv30 - rv20, 4)
    if vrp <= VRP_BUY_ZONE:
        zone = "BUY_OPTIONALITY"
    elif vrp >= VRP_SELL_ZONE:
        zone = "DERISK_SHARES"
    else:
        zone = "NEUTRAL"

    sessions_old = max(len(pd.bdate_range(start=iv30_asof, end=last_session)) - 1, 0)
    stale = sessions_old > IV_STALE_SESS

    return {"iv30": iv30, "iv30_asof": iv30_asof, "stale": stale, "vrp": vrp, "zone": zone}


def tripwires(manual: dict, consec_below_ma200: int) -> dict:
    hyperscaler = bool(manual.get("tripwire_hyperscaler_plateau", False))
    fed_hike = bool(manual.get("tripwire_fed_hike_delivered", False))
    memory_rollover = bool(manual.get("tripwire_memory_rollover", False))
    ma200_break = consec_below_ma200 >= GATE_ZERO_DAYS
    return {
        "hyperscaler_plateau": hyperscaler,
        "fed_hike": fed_hike,
        "memory_rollover": memory_rollover,
        "ma200_break": ma200_break,
        "any": hyperscaler or fed_hike or memory_rollover or ma200_break,
    }


def _accumulate(positions: list[float], rets: list[float], slippage_bps: float = SLIPPAGE_BPS) -> tuple[list[float], list[float]]:
    """Strict next-close accounting: positions[i] already resolved for day i.

    Slippage of slippage_bps * |delta position| is charged on the day a change is set.
    """
    equity: list[float] = []
    bh: list[float] = []
    e, b = 1.0, 1.0
    prev_pos: float | None = None
    for pos, ret in zip(positions, rets):
        slip = (slippage_bps / 10000.0) * abs(pos - prev_pos) if prev_pos is not None else 0.0
        e *= (1 + pos * ret - slip)
        b *= (1 + ret)
        equity.append(e)
        bh.append(b)
        prev_pos = pos
    return equity, bh


def attribution(soxx: pd.DataFrame, soxl: pd.DataFrame) -> dict:
    """Hypothetical always-at-target engine equity vs SOXL buy-and-hold, from BACKTEST_START.

    Position for day t = E_target computed at close t-1 (strict next-close fills).
    """
    ret = soxx["close"].pct_change()
    rv20 = ret.rolling(20).std(ddof=1) * math.sqrt(252)
    rv20_p90 = rv20.rolling(P90_WINDOW, min_periods=P90_MIN_PERIODS).quantile(0.90)
    ma200 = soxx["close"].rolling(200).mean()

    # Before 120 sessions of vol history, rv20_p90 is undefined; fall back to rv20 itself so
    # the p90-gated rules (R1/R2) default to full exposure rather than raising on NaN.
    p90_eff = rv20_p90.fillna(rv20)

    below = soxx["close"] <= ma200
    reset_groups = (~below).cumsum()
    consec = below.groupby(reset_groups).cumcount() + 1
    consec = consec.where(below, 0)

    T = pd.Series(1.0, index=soxx.index)
    T = T.mask((consec >= 1) & (consec < GATE_ZERO_DAYS), GATE_HALF)
    T = T.mask(consec >= GATE_ZERO_DAYS, 0.0)

    rv = rv20.to_numpy()
    p90 = p90_eff.to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        R1 = np.where(rv <= p90, 1.0, np.minimum(1.0, 0.40 / rv))
        R2 = np.where(rv <= p90, 1.0, np.minimum(1.0, 0.50 / rv))
        R3 = np.where(rv <= 0.60, 1.0, np.minimum(1.0, 0.50 / rv))
        R4 = np.where(rv <= 0.55, 1.0, np.minimum(1.0, 0.40 / rv))
    ens = (R1 + R2 + R3 + R4) / 4.0
    e_tgt = np.round(ens * T.to_numpy(), 3)

    e_target_series = pd.Series(e_tgt, index=soxx.index)
    e_target_series[rv20.isna()] = np.nan

    positions = e_target_series.shift(1)

    merged = pd.DataFrame({"position": positions}).join(
        soxl["close"].rename("soxl_close"), how="inner"
    )
    merged["soxl_ret"] = merged["soxl_close"].pct_change()

    start = pd.Timestamp(BACKTEST_START)
    bt = merged[merged.index >= start].dropna(subset=["position", "soxl_ret"])

    equity_engine, equity_bh = _accumulate(bt["position"].tolist(), bt["soxl_ret"].tolist())
    dates = [d.strftime("%Y-%m-%d") for d in bt.index]

    return {
        "dates": dates,
        "equity_engine": [round(v, 6) for v in equity_engine],
        "equity_bh": [round(v, 6) for v in equity_bh],
    }
