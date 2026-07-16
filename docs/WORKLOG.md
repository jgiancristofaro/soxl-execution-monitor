# WORKLOG — SOXL Execution Monitor

> Append-only decision log. NEVER edit old entries. Add new entries at the bottom.
> AI agents: read this index first to understand prior decisions before starting work.

---

## Index

| # | Date | Title |
|---|------|-------|
| [001](#001) | 2026-07-15 | Project built from the SOXL Execution Monitor build spec |

---

### 001

**Date:** 2026-07-15
**Title:** Project built from the SOXL Execution Monitor build spec

Built end-to-end from `SOXL_EXECUTION_MONITOR_BUILD_SPEC.md` (v1.0): pipeline
(`sources.py`/`engine.py`/`compute.py`/`preview.py`), 61 passing tests (T1–T13), the Vite +
vanilla TypeScript + Chart.js dashboard, the four GitHub Actions workflows (early-fire/sleep
pattern per C4), and the methodology page + archive mechanism.

Decisions made where the spec left room for judgment, for future reference:

- **`tranche_states()` / `caps()` signatures** extended beyond the spec's §6.1 listing (added a
  `T` parameter to `tranche_states`, and `tranche_pnls` to `caps`'s return) because the described
  behavior (T3 requires `T >= 0.5`; per-tranche P&L display) needed inputs/outputs the literal
  signatures didn't carry. Behavior matches §3 exactly; only the function signatures differ from
  the listing.
- **Sleeve cap blending (§3.6)** is a capital-weighted average normalized to the *deployed*
  sleeve fraction, not to total C — an unweighted sum of `pct_i * pnl_i` never reaches the -35%
  threshold while less than 100% of C is deployed, which would make the sleeve cap unreachable
  during the exact ramp-up period it exists to protect. The spec's own T5 worked example implies
  a breach at the values given, which only checks out under the normalized interpretation.
- **T10 (attribution) exact values** were pinned after implementing the next-close + slippage
  accounting logic, per the test description's own instruction, rather than hand-matched to the
  spec's illustrative (and internally approximate) prose numbers.
- **`series.rv20_p90`** was added to `signals.json` beyond the §6.3 example schema — PR-9b
  explicitly requires charting the rolling p90 line, which needs this series to exist.
- **Persistent vs. transition alerts**: `compute_signals()` always emits a `cap_breach` alert
  while `caps.sleeve_breach` is true (satisfies the §6.4 invariant 6 unconditionally, including on
  a first-ever run with no previous file); `diff_alerts()` separately emits transition-only alerts
  (new ACT, newly-armed tranche, newly-tripped tripwire) by diffing against the previous settled
  `signals.json`.

---

Research and education only. Not investment advice. A 3x levered fund can lose most of its value
in days.
