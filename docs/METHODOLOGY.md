# Reconciled Plan v1.0 — Condensed Reference

Full narrative version with rationale and evidence tables: `site/public/methodology.html`
(served at `/methodology.html`). This file is the quick technical reference for anyone reading
the code.

## Derived series (on SOXX unless noted)

- `ret_t = close_t/close_{t-1} - 1`
- `rv20 = std(ret, 20) * sqrt(252)` (sample std, ddof=1)
- `rv20_p90` = rolling 252-session 90th percentile of `rv20`, `min_periods=120`
- `ma20/ma50/ma200` = simple moving averages of close
- `id = close/open - 1`; `id20` = rolling 20-session sum of `id`
- SOXL returns are used only for the position ledger, hard-cap P&L, and the attribution backtest

## Sizing rules

| Rule | Trigger | Vol budget |
|---|---|---|
| R1 | `rv20 > rv20_p90` | 0.40 |
| R2 | `rv20 > rv20_p90` | 0.50 |
| R3 | `rv20 > 0.60` | 0.50 |
| R4 | `rv20 > 0.55` | 0.40 |

Each rule is `1.0` if `rv20 <= trigger`, else `min(1.0, budget / rv20)`.
`ENSEMBLE = mean(R1..R4)`.

## Trend gate

- `T = 1.0` while close > MA200
- `T = 0.5` on any close <= MA200
- `T = 0.0` after 5 consecutive closes <= MA200 (sticky; resets on any close > MA200)

`E_target = round(ENSEMBLE * T, 3)`.

## Churn band

`gap = E_target - deployed`; `ACT = abs(gap) >= 0.10` (boundary inclusive).

## Tranches

- T1 (25% of C): discretionary entry; `DEPLOYED` once filled in `position.json`.
- T2 (+20% of C): arms when `rv20 < 0.65` OR `id20 > -0.03`.
- T3 (up to E_target): arms when `manual.gauntlet_cleared` AND `T >= 0.5` AND no tripwire.

## Hard caps

- Per-tranche: `soxl_close/cost_basis - 1 <= -0.25` -> `BREACH-HALVE`.
- Sleeve (capital-weighted blend of deployed tranches): `<= -0.35` -> `BREACH-FLAT`.

## VRP

`vrp = iv30 - rv20`. `<= -0.10` -> BUY_OPTIONALITY. `>= +0.10` -> DERISK_SHARES. Else NEUTRAL.
Stale badge if `iv30_asof` is more than 7 sessions old (zone still computed).

## Tripwires

Three manual flags (hyperscaler capex plateau, delivered Fed hike, TrendForce memory rollover)
plus one computed flag (5 consecutive SOXX closes <= MA200). Any one trips the dashboard-wide
banner.

## Constants

All tunable numbers live in one block at the top of `pipeline/engine.py` — see that file for the
authoritative, currently-live values.

---

Research and education only. Not investment advice. A 3x levered fund can lose most of its value
in days.
