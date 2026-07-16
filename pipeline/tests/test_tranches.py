from pipeline.engine import tranche_states


def _position(t1_status="WAITING", t2_status="WAITING", t3_status="WAITING"):
    return {
        "tranches": [
            {"id": "T1", "status": t1_status, "pct": 0.25, "cost_basis_soxl": None, "fill_date": None},
            {"id": "T2", "status": t2_status, "pct": 0.20, "cost_basis_soxl": None, "fill_date": None},
            {"id": "T3", "status": t3_status, "pct": None, "cost_basis_soxl": None, "fill_date": None},
        ]
    }


def _find(states, tid):
    return next(t for t in states if t["id"] == tid)


def test_t2_waiting_when_neither_trigger_passes():
    states = tranche_states(_position(), rv20=0.712, id20=-0.156, manual={}, tripped=False, T=1.0)
    assert _find(states, "T2")["status"] == "WAITING"


def test_t2_armed_on_low_rv():
    states = tranche_states(_position(), rv20=0.64, id20=-0.156, manual={}, tripped=False, T=1.0)
    assert _find(states, "T2")["status"] == "ARMED"


def test_t2_armed_on_id20_trigger():
    states = tranche_states(_position(), rv20=0.712, id20=-0.02, manual={}, tripped=False, T=1.0)
    assert _find(states, "T2")["status"] == "ARMED"


def test_t3_armed_when_gauntlet_cleared_gate_open_no_tripwire():
    states = tranche_states(
        _position(), rv20=0.712, id20=-0.156,
        manual={"gauntlet_cleared": True}, tripped=False, T=1.0,
    )
    assert _find(states, "T3")["status"] == "ARMED"


def test_t3_not_armed_when_tripwire_tripped():
    states = tranche_states(
        _position(), rv20=0.712, id20=-0.156,
        manual={"gauntlet_cleared": True}, tripped=True, T=1.0,
    )
    assert _find(states, "T3")["status"] != "ARMED"


def test_deployed_tranches_always_reported_deployed():
    states = tranche_states(
        _position(t1_status="DEPLOYED", t2_status="DEPLOYED"),
        rv20=0.712, id20=-0.156, manual={}, tripped=True, T=0.0,
    )
    assert _find(states, "T1")["status"] == "DEPLOYED"
    assert _find(states, "T2")["status"] == "DEPLOYED"


def test_t1_waiting_note_when_not_filled():
    states = tranche_states(_position(), rv20=0.712, id20=-0.156, manual={}, tripped=False, T=1.0)
    t1 = _find(states, "T1")
    assert t1["status"] == "WAITING"
    assert "TSMC" in t1["triggers"][0]["name"]
