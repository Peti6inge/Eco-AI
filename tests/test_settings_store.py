from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.csv_ingest import parse_csv
from app.main import _compare_packs
from app.schema import Settings
from app import settings_store

MINIMAL = {
    "providers": [
        {
            "id": "spacexai",
            "name": "SpaceXAI",
            "mu_L_per_kWh": 2.0,
            "sigma_L_per_kWh": 0.1,
            "mu_kg_per_kWh": 0.4,
            "sigma_kg_per_kWh": 0.05,
        }
    ],
    "models": [
        {
            "id": "x",
            "provider_id": "spacexai",
            "match_prefixes": ["x"],
            "input": 1.0,
            "output": 1.0,
            "cache_read": 1.0,
            "cache_write": 1.0,
            "mu_kWh_per_usd": 0.1,
            "sigma_kWh_per_usd": 0.01,
        }
    ],
}

CSV = (
    "Date,Cloud Agent ID,Automation ID,Kind,Model,Max Mode,"
    "Input (w/ Cache Write),Input (w/o Cache Write),Cache Read,"
    "Output Tokens,Total Tokens,Cost\n"
    "2026-10-02,,,,x,false,1,2,3,4,10,Included\n"
)


@pytest.fixture
def packs_dir(tmp_path, monkeypatch):
    directory = tmp_path / "settings"
    monkeypatch.setattr(settings_store, "SETTINGS_DIR", directory)
    return directory


def test_seed_creates_cursor_from_defaults(packs_dir):
    packs = settings_store.list_packs()
    assert packs == ["cursor"]
    settings = settings_store.load_settings()
    assert settings.models
    assert (packs_dir / "cursor.json").is_file()


def test_list_existing_json_files(packs_dir):
    packs_dir.mkdir()
    (packs_dir / "chatgpt.json").write_text(json.dumps(MINIMAL), encoding="utf-8")
    (packs_dir / "claude.json").write_text(json.dumps(MINIMAL), encoding="utf-8")
    assert settings_store.list_packs() == ["chatgpt", "claude"]
    assert settings_store.default_pack() == "chatgpt"
    loaded = settings_store.load_settings("claude")
    assert loaded.models[0].id == "x"


def test_unknown_and_invalid_pack(packs_dir):
    packs_dir.mkdir()
    (packs_dir / "cursor.json").write_text(json.dumps(MINIMAL), encoding="utf-8")
    with pytest.raises(settings_store.UnknownPackError):
        settings_store.load_settings("absent")
    with pytest.raises(settings_store.InvalidPackError):
        settings_store.load_settings("../secrets")


def test_compare_packs_returns_quartiles(packs_dir):
    packs_dir.mkdir()
    light = json.loads(json.dumps(MINIMAL))
    heavy = json.loads(json.dumps(MINIMAL))
    heavy["models"][0]["mu_kWh_per_usd"] = 0.5
    (packs_dir / "light.json").write_text(json.dumps(light), encoding="utf-8")
    (packs_dir / "heavy.json").write_text(json.dumps(heavy), encoding="utf-8")
    rows = parse_csv(CSV).rows
    table = _compare_packs(rows, n_draws=800)
    by_id = {row["pack"]: row for row in table}
    assert set(by_id) == {"heavy", "light"}
    assert by_id["heavy"]["co2"]["median"] > by_id["light"]["co2"]["median"]
    assert by_id["heavy"]["water"]["median"] > by_id["light"]["water"]["median"]
    Settings.model_validate(MINIMAL)
