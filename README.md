# SOXL Execution Monitor

Live dashboard: **https://jgiancristofaro.github.io/soxl-execution-monitor/**

An auto-updating execution dashboard for a systematic SOXL (3x leveraged semiconductor ETF)
position-sizing plan — the **Reconciled Plan v1.0**. It turns realized volatility and trend on
the unlevered SOXX index into a target exposure number, tracks a 3-tranche re-deployment plan,
monitors hard risk caps against the actual position ledger, and displays a sibling project's
research signal as context only.

Full methodology: [site/public/methodology.html](site/public/methodology.html) (served at
`/methodology.html` on the live site).

## The engine-decides, monitor-informs principle

This repo has a sibling project, [soxx-regime-monitor](https://github.com/jgiancristofaro/soxx-regime-monitor),
which watches SOXX for institutional distribution — a *research* signal. This project is the
*execution* system. They are kept as two separate dashboards, each with its own equity curve,
trade log, and git history, on purpose:

- **The engine decides.** Every number that drives ACT/HOLD, tranche state, and hard-cap status
  is computed from this repo's own SOXX/SOXL price history and the human-edited ledger files
  below — never from the sibling feed.
- **The monitor informs.** The sibling's `signals.json` is fetched once, server-side, in the
  pipeline, and surfaced as a clearly subordinate "input, not a trigger" panel. A static test
  (`pipeline/tests/test_isolation.py`) asserts the sizing engine's source code never references
  the sibling feed's identifiers, so this boundary can't silently erode over time.

## Editing the ledger files after a real trade

These three files are **human-edited, not pipeline-written** — the pipeline reads them but never
writes to them, because fills are ground truth and should never be guessed:

- **`data/position.json`** — the tranche ledger. After a real fill, set that tranche's `status`
  to `"DEPLOYED"`, fill in `pct` (if not already set), `cost_basis_soxl` (your SOXL fill price),
  and `fill_date` (`YYYY-MM-DD`). This is what `deployed`, the churn gap, and the hard-cap P&L are
  all computed from.
- **`data/manual.json`** — `iv30`/`iv30_asof` (update whenever you get a fresh implied-vol
  reading), `gauntlet_cleared` (flip to arm T3), and the three manual tripwire flags (§4 of the
  methodology). Any of these flips takes effect on the next pipeline run.
- **`data/events.json`** — the event calendar. Add upcoming earnings/FOMC dates as
  `{"date": "YYYY-MM-DD", "label": "..."}`; the dashboard computes the countdown and no-add
  window automatically.

## Workflow schedule

GitHub Actions cron jitter on this account has been observed at 60–70 minutes, so every scheduled
workflow **fires 90–110 minutes early and sleeps until the exact ET target** via
`scripts/wait_until.py` (DST-safe; a dual EDT/EST cron pair makes the pair self-correcting — in
the wrong season one cron just sleeps longer). Do not replace this with a plain cron at the
target time.

| Workflow | Target (ET) | Cron (fires early) | Writes |
|---|---|---|---|
| `preview.yml` | 15:50 | `18:00` / `19:00` UTC (EDT/EST) | `data/preview.json` only |
| `daily.yml` | 17:30 | `20:00` / `21:00` UTC (EDT/EST) | `data/signals.json`, opens alert issues |
| `deploy.yml` | on push to `main` touching `site/**` or `data/*.json`, or manual | — | builds & publishes `site/dist` to Pages |
| `ci.yml` | on push/PR to `main` | — | pytest + `tsc --noEmit` + `vite build` |

## Local development

```bash
# Pipeline
pip install -r pipeline/requirements.txt
python -m pytest pipeline/tests/ -v      # all tests, offline (fixture-based)
python pipeline/compute.py               # live settle run -> data/signals.json
python pipeline/preview.py               # live preview run -> data/preview.json

# Site
cd site
npm ci
npm run dev          # http://localhost:5173/soxl-execution-monitor/
npx tsc --noEmit
npm run build         # -> site/dist
npm run preview
```

## Repository layout

See `pipeline/` (fetch → derive → engine → validate → write), `data/` (pipeline output +
human-edited ledger), `site/` (Vite + vanilla TypeScript + Chart.js dashboard, no framework),
`.github/workflows/` (the four workflows above), `docs/` (condensed methodology + worklog).

---

Research and education only. Not investment advice. A 3x levered fund can lose most of its value
in days.
