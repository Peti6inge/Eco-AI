from __future__ import annotations

import json
from pathlib import Path

from app.schema import Settings

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = ROOT / "defaults" / "settings.json"
DATA_DIR = ROOT / "data"
DATA_PATH = DATA_DIR / "settings.json"


def seed_if_missing() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(DEFAULTS_PATH.read_text(encoding="utf-8"), encoding="utf-8")


def load_settings() -> Settings:
    seed_if_missing()
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return Settings.model_validate(raw)


def save_settings(settings: Settings) -> Settings:
    seed_if_missing()
    DATA_PATH.write_text(
        settings.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return settings
