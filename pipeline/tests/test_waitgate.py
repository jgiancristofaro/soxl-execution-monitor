import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from wait_until import MISCONFIG_SENTINEL, resolve_sleep_seconds, seconds_until  # noqa: E402

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def utc_for_et(s: str) -> datetime:
    """'YYYY-MM-DD HH:MM ET' -> aware UTC datetime."""
    date_part, time_part, _tz = s.split(" ")
    naive = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=ET).astimezone(UTC)


def test_edt_target_still_ahead():
    # 2026-07-16 is EDT. 16:00 ET -> 17:30 ET target = 90 minutes = 5400s.
    assert seconds_until("17:30", utc_for_et("2026-07-16 16:00 ET")) == 5400


def test_target_already_passed_returns_zero():
    assert seconds_until("15:50", utc_for_et("2026-07-16 16:00 ET")) == 0


def test_dst_safe_january_est():
    # 2026-01-15 is EST. 14:00 ET -> 17:30 ET = 3.5h = 12600s.
    secs = seconds_until("17:30", utc_for_et("2026-01-15 14:00 ET"))
    assert secs == 12600


def test_dst_safe_july_edt():
    # 2026-07-15 is EDT. 14:00 ET -> 17:30 ET = 3.5h = 12600s (same ET arithmetic
    # regardless of DST, since both now and target are expressed in ET wall-clock).
    secs = seconds_until("17:30", utc_for_et("2026-07-15 14:00 ET"))
    assert secs == 12600


def test_misconfig_sentinel_when_exceeding_max_hours():
    now = utc_for_et("2026-07-16 08:00 ET")  # 17:30 target is 9.5h away
    result = resolve_sleep_seconds("17:30", now, max_hours=3.0)
    assert result == MISCONFIG_SENTINEL


def test_within_max_hours_returns_seconds():
    now = utc_for_et("2026-07-16 16:00 ET")
    result = resolve_sleep_seconds("17:30", now, max_hours=3.0)
    assert result == 5400
