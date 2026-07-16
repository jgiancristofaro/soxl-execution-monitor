"""3:50pm ET preview run: same computation on the live (unsettled) candle -> data/preview.json.

Never writes signals.json, never opens issues (§6.6). Keeps the intraday bar the settle
pipeline's live-candle guard would otherwise drop -- purpose is the MOC execution decision
minutes before the close.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timezone

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.compute import (
    DATA_DIR,
    SITE_DATA_DIR,
    _write_json,
    compute_signals,
    load_events,
    load_manual,
    load_position,
)
from pipeline.sources import fetch_ohlcv, fetch_upstream

PREVIEW_PATH = DATA_DIR / "preview.json"


def main() -> None:
    manual = load_manual()
    position = load_position()
    events = load_events()

    soxx = fetch_ohlcv("SOXX", days=600)
    soxl = fetch_ohlcv("SOXL", days=600)
    upstream = fetch_upstream()
    generated_utc = datetime.now(timezone.utc).isoformat()

    preview = compute_signals(
        soxx, soxl, upstream, manual, position, events,
        generated_utc=generated_utc, data_stale=False, is_preview=True,
    )

    _write_json(PREVIEW_PATH, preview)
    _write_json(SITE_DATA_DIR / "preview.json", preview)
    print(f"Wrote preview.json for {preview['last_session']}: "
          f"e_target={preview['engine']['e_target']} act={preview['engine']['act']}")


if __name__ == "__main__":
    main()
