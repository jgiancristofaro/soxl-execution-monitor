from pipeline.compute import apply_stale_guard, compute_signals


def test_second_run_same_session_no_new_alerts_last_session_unchanged(soxx_df, soxl_df, manual, position, events):
    first = compute_signals(
        soxx_df, soxl_df, upstream=None, manual=manual, position=position, events=events,
        generated_utc="2026-07-15T22:00:00+00:00",
    )
    assert first["last_session"] == "2026-07-15"

    guarded = apply_stale_guard(
        previous=first, last_session="2026-07-15",
        generated_utc="2026-07-15T23:00:00+00:00", data_stale=False,
    )

    assert guarded is not None
    assert guarded["last_session"] == first["last_session"]
    assert guarded["generated_utc"] == "2026-07-15T23:00:00+00:00"
    # alerts are cleared, not carried forward -- otherwise the daily workflow's issue-creation
    # step would re-open the same GH issue on every subsequent guarded (no-new-session) day
    assert guarded["alerts"] == []


def test_new_session_returns_none_signals_recompute_needed(soxx_df, soxl_df, manual, position, events):
    first = compute_signals(
        soxx_df, soxl_df, upstream=None, manual=manual, position=position, events=events,
        generated_utc="2026-07-15T22:00:00+00:00",
    )
    guarded = apply_stale_guard(
        previous=first, last_session="2026-07-16",
        generated_utc="2026-07-16T22:00:00+00:00", data_stale=False,
    )
    assert guarded is None


def test_no_previous_file_returns_none():
    guarded = apply_stale_guard(
        previous=None, last_session="2026-07-15",
        generated_utc="2026-07-15T22:00:00+00:00", data_stale=False,
    )
    assert guarded is None
