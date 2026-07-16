"""Sleep until a target America/New_York wall-clock time today. DST-safe.

Usage: python scripts/wait_until.py --et 17:30 [--max-hours 3]

Exits 0 immediately if target already passed. Exits 1 if sleep would exceed --max-hours
(cron misconfig guard) -- see C4: workflows fire ~90-110min early and sleep until the exact
ET target, since GitHub cron jitter on this account has been observed at 60-70 minutes.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
MISCONFIG_SENTINEL = -1


def seconds_until(target_hhmm: str, now_utc: datetime) -> int:
    """Seconds from now_utc until target_hhmm ET today. 0 if already passed."""
    now_et = now_utc.astimezone(ET)
    hour, minute = (int(x) for x in target_hhmm.split(":"))
    target_et = now_et.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target_et <= now_et:
        return 0
    return int((target_et - now_et).total_seconds())


def resolve_sleep_seconds(target_hhmm: str, now_utc: datetime, max_hours: float) -> int:
    """Seconds to sleep, or MISCONFIG_SENTINEL if that would exceed max_hours."""
    secs = seconds_until(target_hhmm, now_utc)
    if secs > max_hours * 3600:
        return MISCONFIG_SENTINEL
    return secs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--et", required=True, help="target ET time, HH:MM")
    parser.add_argument("--max-hours", type=float, default=3.0)
    args = parser.parse_args()

    now_utc = datetime.now(tz=ZoneInfo("UTC"))
    secs = resolve_sleep_seconds(args.et, now_utc, args.max_hours)

    if secs == MISCONFIG_SENTINEL:
        print(
            f"Refusing to sleep: target {args.et} ET is more than {args.max_hours}h away "
            f"from now ({now_utc.isoformat()}) -- likely a cron misconfiguration.",
            file=sys.stderr,
        )
        sys.exit(1)

    if secs == 0:
        print(f"Target {args.et} ET already passed; continuing immediately.")
        return

    print(f"Sleeping {secs}s until {args.et} ET...")
    remaining = secs
    while remaining > 0:
        chunk = min(60, remaining)
        time.sleep(chunk)
        remaining -= chunk
        if remaining > 0:
            print(f"  {remaining}s remaining...")
    print("Wake.")


if __name__ == "__main__":
    main()
