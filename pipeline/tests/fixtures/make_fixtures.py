"""Run once during build: fetch live SOXX/SOXL OHLCV through 2026-07-15, write CSV fixtures
and golden.json (the pinned engine outputs future refactors must reproduce exactly).

Usage: python -m pipeline.tests.fixtures.make_fixtures
"""
from __future__ import annotations

import json
import math
import pathlib

import pandas as pd

from pipeline import engine
from pipeline.sources import fetch_ohlcv

CUTOFF = "2026-07-15"
FIXTURES_DIR = pathlib.Path(__file__).resolve().parent


def _truncate(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.index <= pd.Timestamp(CUTOFF)]


def main() -> None:
    soxx = _truncate(fetch_ohlcv("SOXX", days=900))
    soxl = _truncate(fetch_ohlcv("SOXL", days=900))

    if soxx.index[-1].strftime("%Y-%m-%d") != CUTOFF:
        raise RuntimeError(
            f"live fetch did not include the {CUTOFF} session as the last row "
            f"(got {soxx.index[-1].date()}) -- halting rather than fabricating fixture data"
        )

    soxx.to_csv(FIXTURES_DIR / "soxx_daily.csv", index_label="date")
    soxl.to_csv(FIXTURES_DIR / "soxl_daily.csv", index_label="date")

    ret = soxx["close"].pct_change()
    rv20 = ret.rolling(20).std(ddof=1) * math.sqrt(252)
    rv20_p90 = rv20.rolling(engine.P90_WINDOW, min_periods=engine.P90_MIN_PERIODS).quantile(0.90)
    ma200 = soxx["close"].rolling(200).mean()
    id_ = soxx["close"] / soxx["open"] - 1
    id20 = id_.rolling(20).sum()

    last_rv20 = float(rv20.iloc[-1])
    last_p90 = float(rv20_p90.iloc[-1])
    rules = engine.sizing_rules(last_rv20, last_p90)
    ens = engine.ensemble(rules)
    T, consec = engine.trend_gate(soxx["close"], ma200)
    e_tgt = engine.e_target(ens, T)
    last_id20 = float(id20.iloc[-1])
    vrp = engine.vrp_zone(0.46, "2026-07-01", last_rv20, CUTOFF)

    golden = {
        "last_session": CUTOFF,
        "soxx_close": float(soxx["close"].iloc[-1]),
        "soxl_close": float(soxl["close"].iloc[-1]),
        "ma200": float(ma200.iloc[-1]),
        "rv20": round(last_rv20, 6),
        "rv20_p90": round(last_p90, 6),
        "rules": {k: round(v, 6) for k, v in rules.items()},
        "ensemble": round(ens, 6),
        "T": T,
        "consec_below_ma200": consec,
        "e_target": e_tgt,
        "id20": round(last_id20, 6),
        "vrp": vrp,
    }
    (FIXTURES_DIR / "golden.json").write_text(json.dumps(golden, indent=2) + "\n")
    print(json.dumps(golden, indent=2))


if __name__ == "__main__":
    main()
