from __future__ import annotations

import json
from pathlib import Path

from app.csv_ingest import match_model
from app.schema import ModelConfig, Settings

DEFAULTS = json.loads(
    (Path(__file__).resolve().parents[1] / "defaults" / "settings.json").read_text(
        encoding="utf-8"
    )
)
MODELS = Settings.model_validate(DEFAULTS).models


def _ids(*csv_names: str) -> list[str | None]:
    return [m.id if (m := match_model(name, MODELS)) else None for name in csv_names]


def test_longest_prefix_grok_and_opus():
    assert match_model("cursor-grok-4.6-medium", MODELS).id == "cursor-grok-4.6"
    assert match_model("cursor-grok-4.6-high-fast", MODELS).id == "cursor-grok-4.6"
    assert match_model("claude-opus-5-5-high", MODELS).id == "claude-opus-5"
    assert match_model("auto", MODELS).id == "auto"


def test_composer_fast_beats_generic_composer():
    assert match_model("composer-2.5", MODELS).id == "composer-2.5"
    assert match_model("composer-2.5-fast", MODELS).id == "composer-2.5-fast"
    assert match_model("composer-2.5-fast-high", MODELS).id == "composer-2.5-fast"


def test_unknown_models_are_none():
    assert match_model("gemini-3.1-pro", MODELS) is None
    assert match_model("gpt-5.6-high", MODELS) is None


def test_custom_prefix_length():
    models = [
        ModelConfig(
            id="ab",
            provider_id="spacexai",
            match_prefixes=["ab"],
            input=0,
            output=0,
            cache_read=0,
            cache_write=0,
            mu_kWh_per_usd=0.1,
            sigma_kWh_per_usd=0.01,
        ),
        ModelConfig(
            id="abcd",
            provider_id="spacexai",
            match_prefixes=["abcd"],
            input=0,
            output=0,
            cache_read=0,
            cache_write=0,
            mu_kWh_per_usd=0.1,
            sigma_kWh_per_usd=0.01,
        ),
    ]
    assert match_model("abcdef", models).id == "abcd"
    assert match_model("ab0", models).id == "ab"
