from __future__ import annotations

import json
import re
from pathlib import Path

from app.schema import Settings

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = ROOT / "defaults" / "settings.json"
DATA_DIR = ROOT / "data"
SETTINGS_DIR = DATA_DIR / "settings"

_PACK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class UnknownPackError(KeyError):
    pass


class InvalidPackError(ValueError):
    pass


def seed_if_missing() -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    if not any(SETTINGS_DIR.glob("*.json")):
        (SETTINGS_DIR / "cursor.json").write_text(
            DEFAULTS_PATH.read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def list_packs() -> list[str]:
    seed_if_missing()
    return sorted(path.stem for path in SETTINGS_DIR.glob("*.json"))


def default_pack() -> str:
    packs = list_packs()
    if "cursor" in packs:
        return "cursor"
    if not packs:
        raise UnknownPackError("Aucun jeu de paramètres dans data/settings.")
    return packs[0]


def _pack_path(pack_id: str) -> Path:
    if not pack_id or not _PACK_ID.fullmatch(pack_id):
        raise InvalidPackError("Identifiant de jeu invalide.")
    path = (SETTINGS_DIR / f"{pack_id}.json").resolve()
    if path.parent != SETTINGS_DIR.resolve():
        raise InvalidPackError("Identifiant de jeu invalide.")
    return path


def load_settings(pack_id: str | None = None) -> Settings:
    seed_if_missing()
    chosen = pack_id or default_pack()
    path = _pack_path(chosen)
    if not path.is_file():
        raise UnknownPackError(f"Jeu inconnu : {chosen}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Settings.model_validate(raw)


def load_all_settings() -> list[tuple[str, Settings]]:
    return [(pack_id, load_settings(pack_id)) for pack_id in list_packs()]


def save_settings(settings: Settings, pack_id: str | None = None) -> Settings:
    seed_if_missing()
    chosen = pack_id or default_pack()
    path = _pack_path(chosen)
    if not path.is_file():
        raise UnknownPackError(f"Jeu inconnu : {chosen}")
    path.write_text(settings.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return settings
