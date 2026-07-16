"""Orchestrator: fetch -> derive -> engine -> validate -> write data/signals.json.

Settle pipeline only (close-based, C3). See preview.py for the 3:50pm ET preview run.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Allow `python pipeline/compute.py` (workflow invocation) as well as `python -m
    # pipeline.compute` -- running a script directly only puts its own directory on sys.path.
    sys.path.insert(0, str(ROOT))

from pipeline import engine
from pipeline.sources import fetch_ohlcv, fetch_upstream, load_fixture
DATA_DIR = ROOT / "data"
FIXTURES_DIR = ROOT / "pipeline" / "tests" / "fixtures"
SITE_DATA_DIR = ROOT / "site" / "public" / "data"
SIGNALS_PATH = DATA_DIR / "signals.json"


def _load_json(path: pathlib.Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_manual() -> dict:
    return _load_json(DATA_DIR / "manual.json") or {}


def load_position() -> dict:
    data = _load_json(DATA_DIR / "position.json")
    if data is None:
        raise RuntimeError("data/position.json is missing -- ground truth of fills, never guess")
    return data


def load_events() -> list:
    return _load_json(DATA_DIR / "events.json") or []


def drop_unsettled_last_bar(df: pd.DataFrame) -> pd.DataFrame:
    """Live-candle guard (C3, §6.5): never treat an intraday price as a settled close."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if df.index[-1].date() == now_et.date() and now_et.time() < time(16, 5):
        return df.iloc[:-1]
    return df


def compute_signals(
    soxx: pd.DataFrame,
    soxl: pd.DataFrame,
    upstream: dict | None,
    manual: dict,
    position: dict,
    events: list,
    generated_utc: str,
    data_stale: bool = False,
    is_preview: bool = False,
) -> dict:
    """Pure assembly: fetch/network concerns live in main(); this only transforms inputs."""
    ret = soxx["close"].pct_change()
    rv20 = ret.rolling(20).std(ddof=1) * math.sqrt(252)
    rv20_p90 = rv20.rolling(engine.P90_WINDOW, min_periods=engine.P90_MIN_PERIODS).quantile(0.90)
    ma200 = soxx["close"].rolling(200).mean()
    id_ = soxx["close"] / soxx["open"] - 1
    id20 = id_.rolling(20).sum()
    soxl_ret = soxl["close"].pct_change()

    last_session = soxx.index[-1].strftime("%Y-%m-%d")
    soxx_close = float(soxx["close"].iloc[-1])
    soxl_close = float(soxl["close"].iloc[-1])

    last_rv20 = float(rv20.iloc[-1])
    p90_raw = rv20_p90.iloc[-1]
    last_p90 = float(p90_raw) if not pd.isna(p90_raw) else last_rv20
    rules = engine.sizing_rules(last_rv20, last_p90)
    ens = engine.ensemble(rules)
    T, consec = engine.trend_gate(soxx["close"], ma200)
    e_tgt = engine.e_target(ens, T)
    deployed = sum(t["pct"] for t in position["tranches"] if t["status"] == "DEPLOYED" and t["pct"])
    gap, act = engine.churn(e_tgt, deployed)

    last_id20 = float(id20.iloc[-1])
    trip = engine.tripwires(manual, consec)
    tranches = engine.tranche_states(position, last_rv20, last_id20, manual, trip["any"], T)
    cap_result = engine.caps(position, soxl_close)
    for tr in tranches:
        tr["pnl"] = cap_result["tranche_pnls"].get(tr["id"])

    vrp = engine.vrp_zone(manual.get("iv30"), manual.get("iv30_asof"), last_rv20, last_session)
    attrib = engine.attribution(soxx, soxl)

    events_out = []
    for ev in events:
        ev_date = pd.Timestamp(ev["date"])
        days_until = (ev_date - pd.Timestamp(last_session)).days
        in_window = 0 <= days_until <= (engine.EVENT_NOADD_H / 24)
        events_out.append({**ev, "days_until": days_until, "in_noadd_window": bool(in_window)})

    if upstream is not None:
        upstream_out = {"available": True, **upstream}
    else:
        upstream_out = {
            "available": False, "state": None, "id20": None,
            "on20": None, "dist20": None, "last_session": None,
        }

    series_dates = [d.strftime("%Y-%m-%d") for d in soxx.index]
    rv20_list = rv20.tolist()
    p90_list = rv20_p90.tolist()
    ma200_list = ma200.tolist()
    close_list = soxx["close"].tolist()

    e_target_hist: list[float | None] = []
    below_streak = 0
    for i in range(len(series_dates)):
        if pd.isna(rv20_list[i]) or pd.isna(ma200_list[i]):
            e_target_hist.append(None)
            continue
        p90v = p90_list[i] if not pd.isna(p90_list[i]) else rv20_list[i]
        r = engine.sizing_rules(rv20_list[i], p90v)
        en = engine.ensemble(r)
        is_below = close_list[i] <= ma200_list[i]
        below_streak = below_streak + 1 if is_below else 0
        if below_streak >= engine.GATE_ZERO_DAYS:
            Ti = 0.0
        elif below_streak >= 1:
            Ti = engine.GATE_HALF
        else:
            Ti = 1.0
        e_target_hist.append(engine.e_target(en, Ti))

    soxl_aligned = soxl["close"].reindex(soxx.index).ffill().bfill()

    date_index = {d: i for i, d in enumerate(series_dates)}
    equity_engine_full: list[float | None] = [None] * len(series_dates)
    equity_bh_full: list[float | None] = [None] * len(series_dates)
    for d, e, b in zip(attrib["dates"], attrib["equity_engine"], attrib["equity_bh"]):
        if d in date_index:
            equity_engine_full[date_index[d]] = e
            equity_bh_full[date_index[d]] = b

    tranche_marks = [
        {"id": t["id"], "date": t["fill_date"]}
        for t in position["tranches"] if t.get("fill_date")
    ]

    alerts: list[dict] = []
    if cap_result["sleeve_breach"]:
        alerts.append({
            "type": "cap_breach",
            "title": "Sleeve cap breached — BREACH-FLAT",
            "body": f"Blended sleeve P&L {cap_result['sleeve_pnl']} <= {engine.CAP_SLEEVE}. "
                    f"Overrides everything.",
        })
    for tid in cap_result["tranche_breaches"]:
        alerts.append({
            "type": "cap_breach",
            "title": f"{tid} tranche cap breached — BREACH-HALVE",
            "body": f"{tid} P&L <= {engine.CAP_TRANCHE}.",
        })

    signals = {
        "last_session": last_session,
        "generated_utc": generated_utc,
        "data_stale": data_stale,
        "is_preview": is_preview,
        "market": {
            "soxx_close": soxx_close,
            "soxl_close": soxl_close,
            "soxx_ret": round(float(ret.iloc[-1]), 6),
            "soxl_ret": round(float(soxl_ret.iloc[-1]), 6),
        },
        "engine": {
            "rv20": round(last_rv20, 6),
            "rv20_p90": round(last_p90, 6),
            "rules": {k: round(v, 6) for k, v in rules.items()},
            "ensemble": round(ens, 6),
            "gate": {"T": T, "consec_below_ma200": consec, "ma200": round(float(ma200.iloc[-1]), 4)},
            "e_target": e_tgt,
            "deployed": round(deployed, 6),
            "gap": round(gap, 6),
            "act": act,
        },
        "tranches": tranches,
        "caps": {
            "tranche_breaches": cap_result["tranche_breaches"],
            "sleeve_pnl": cap_result["sleeve_pnl"],
            "sleeve_breach": cap_result["sleeve_breach"],
        },
        "vrp": vrp,
        "tripwires": trip,
        "events": events_out,
        "upstream": upstream_out,
        "series": {
            "dates": series_dates,
            "soxl_close": [round(v, 4) for v in soxl_aligned.tolist()],
            "rv20": [round(v, 6) if not pd.isna(v) else None for v in rv20_list],
            "rv20_p90": [round(v, 6) if not pd.isna(v) else None for v in p90_list],
            "e_target": e_target_hist,
            "equity_engine": equity_engine_full,
            "equity_bh": equity_bh_full,
            "tranche_marks": tranche_marks,
        },
        "checklist": [
            {"label": "E_target", "value": e_tgt},
            {"label": "rv20", "value": round(last_rv20, 4)},
            {"label": "gap / ACT", "value": round(gap, 4), "act": act},
            {"label": "id20 (upstream)", "value": upstream_out.get("id20")},
            {
                "label": "days to next event window",
                "value": min(
                    (e["days_until"] for e in events_out if e["days_until"] >= 0), default=None
                ),
            },
        ],
        "alerts": alerts,
    }
    return signals


def diff_alerts(previous: dict | None, signals: dict) -> list[dict]:
    """New-state alerts computed by diffing against the previous settled signals.json.

    Only transitions fire here (act flips true, a tranche newly arms, a tripwire newly trips) --
    persistent state (e.g. an unresolved sleeve breach) is instead surfaced unconditionally by
    compute_signals() itself so the §6.4 invariant (sleeve_breach implies an alert) holds even
    on the very first run, with no previous file to diff against.
    """
    alerts: list[dict] = []
    prev_act = bool(previous["engine"]["act"]) if previous else False
    if signals["engine"]["act"] and not prev_act:
        alerts.append({
            "type": "act",
            "title": f"ACT — rebalance to target {signals['engine']['e_target']}",
            "body": "Rebalance to target at MOC — never at the open.",
        })

    prev_tranches = {t["id"]: t["status"] for t in previous["tranches"]} if previous else {}
    for t in signals["tranches"]:
        if t["status"] == "ARMED" and prev_tranches.get(t["id"]) != "ARMED":
            alerts.append({
                "type": "tranche_armed",
                "title": f"{t['id']} newly ARMED",
                "body": f"{t['id']} trigger conditions now pass.",
            })

    prev_trip = bool(previous["tripwires"]["any"]) if previous else False
    if signals["tripwires"]["any"] and not prev_trip:
        alerts.append({
            "type": "tripwire",
            "title": "Tripwire newly tripped",
            "body": "Methodology review required; base case invalidated.",
        })

    return alerts


def apply_stale_guard(
    previous: dict | None, last_session: str, generated_utc: str, data_stale: bool
) -> dict | None:
    """Stale/holiday guard (§6.5): same session as last write -> patch metadata only, no
    recompute, no new alerts. Returns None when a full recompute is needed instead."""
    if previous and previous.get("last_session") == last_session:
        patched = dict(previous)
        patched["generated_utc"] = generated_utc
        patched["data_stale"] = data_stale
        return patched
    return None


def validate_consistency(signals: dict) -> None:
    """§6.4 invariants. Raises ValueError on the first violation."""
    engine_ = signals["engine"]
    gap, act = engine_["gap"], engine_["act"]
    if act != (abs(gap) >= engine.CHURN_BAND - 1e-9):
        raise ValueError("invariant 1 violated: act != (abs(gap) >= CHURN_BAND)")

    expected_e_target = round(engine_["ensemble"] * engine_["gate"]["T"], 3)
    if abs(engine_["e_target"] - expected_e_target) > 1e-9:
        raise ValueError("invariant 2 violated: e_target != round(ensemble * T, 3)")

    deployed_sum = sum(t["pct"] for t in signals["tranches"] if t["status"] == "DEPLOYED" and t["pct"])
    if abs(engine_["deployed"] - deployed_sum) > 1e-9:
        raise ValueError("invariant 3 violated: deployed != sum of DEPLOYED pct")

    T = engine_["gate"]["T"]
    consec = engine_["gate"]["consec_below_ma200"]
    ma200_break = signals["tripwires"]["ma200_break"]
    if T not in (1.0, 0.5, 0.0):
        raise ValueError("invariant 4 violated: gate.T not in {1.0, 0.5, 0.0}")
    if (T == 0.0) != (consec >= engine.GATE_ZERO_DAYS):
        raise ValueError("invariant 4 violated: T==0.0 iff consec_below_ma200 >= GATE_ZERO_DAYS")
    if (consec >= engine.GATE_ZERO_DAYS) != ma200_break:
        raise ValueError("invariant 4 violated: consec >= GATE_ZERO_DAYS iff tripwires.ma200_break")

    n_dates = len(signals["series"]["dates"])
    for key in ("soxl_close", "rv20", "rv20_p90", "e_target", "equity_engine", "equity_bh"):
        if len(signals["series"][key]) != n_dates:
            raise ValueError(f"invariant 5 violated: series.{key} length != series.dates length")

    if signals["caps"]["sleeve_breach"]:
        if not any(a.get("type") == "cap_breach" for a in signals["alerts"]):
            raise ValueError("invariant 6 violated: sleeve_breach requires a cap_breach alert")


def main() -> None:
    manual = load_manual()
    position = load_position()
    events = load_events()

    try:
        soxx = drop_unsettled_last_bar(fetch_ohlcv("SOXX", days=600))
        soxl = drop_unsettled_last_bar(fetch_ohlcv("SOXL", days=600))
        data_stale = False
    except Exception:
        soxx = load_fixture(str(FIXTURES_DIR / "soxx_daily.csv"))
        soxl = load_fixture(str(FIXTURES_DIR / "soxl_daily.csv"))
        data_stale = True

    upstream = fetch_upstream()
    generated_utc = datetime.now(timezone.utc).isoformat()

    previous = _load_json(SIGNALS_PATH)
    last_session = soxx.index[-1].strftime("%Y-%m-%d")

    guarded = apply_stale_guard(previous, last_session, generated_utc, data_stale)
    if guarded is not None:
        _write_json(SIGNALS_PATH, guarded)
        _write_json(SITE_DATA_DIR / "signals.json", guarded)
        print(f"No new session ({last_session}); refreshed generated_utc/data_stale only.")
        return

    signals = compute_signals(
        soxx, soxl, upstream, manual, position, events,
        generated_utc=generated_utc, data_stale=data_stale, is_preview=False,
    )
    signals["alerts"] = signals["alerts"] + diff_alerts(previous, signals)

    validate_consistency(signals)

    _write_json(SIGNALS_PATH, signals)
    _write_json(SITE_DATA_DIR / "signals.json", signals)
    print(f"Wrote signals.json for {last_session}: "
          f"e_target={signals['engine']['e_target']} act={signals['engine']['act']}")


if __name__ == "__main__":
    main()
