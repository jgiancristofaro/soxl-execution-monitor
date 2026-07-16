import json
import pathlib

import pytest

from pipeline.sources import load_fixture

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def soxx_df():
    return load_fixture(str(FIXTURES_DIR / "soxx_daily.csv"))


@pytest.fixture(scope="session")
def soxl_df():
    return load_fixture(str(FIXTURES_DIR / "soxl_daily.csv"))


@pytest.fixture(scope="session")
def golden():
    return json.loads((FIXTURES_DIR / "golden.json").read_text())


@pytest.fixture
def manual():
    return {
        "iv30": 0.46, "iv30_asof": "2026-07-01",
        "gauntlet_cleared": False,
        "tripwire_hyperscaler_plateau": False,
        "tripwire_fed_hike_delivered": False,
        "tripwire_memory_rollover": False,
    }


@pytest.fixture
def position():
    return {
        "sleeve_note": "C = capital sleeve committed to the plan.",
        "cash_pct": 1.0,
        "tranches": [
            {"id": "T1", "status": "WAITING", "pct": 0.25, "cost_basis_soxl": None, "fill_date": None},
            {"id": "T2", "status": "WAITING", "pct": 0.20, "cost_basis_soxl": None, "fill_date": None},
            {"id": "T3", "status": "WAITING", "pct": None, "cost_basis_soxl": None, "fill_date": None},
        ],
    }


@pytest.fixture
def events():
    return [
        {"date": "2026-07-16", "label": "TSMC Q2 earnings (pre-market)"},
        {"date": "2026-09-16", "label": "FOMC (SEP)"},
    ]
