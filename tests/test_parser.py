from __future__ import annotations

from pathlib import Path

import pytest

from app.csv_ingest import COL_CACHE_WRITE, COL_INPUT, CsvContractError, parse_csv
from app.schema import Settings
from app.settings_store import DEFAULTS_PATH

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "usage-events-2026-10-02__2__43a7.csv"


def test_example_csv_parses_and_maps_cache_write_vs_input():
    ingested = parse_csv(FIXTURE.read_text(encoding="utf-8"))
    assert ingested.skipped_empty == 2
    assert len(ingested.rows) == 223
    assert ingested.date_min is not None
    assert ingested.date_max is not None

    text = FIXTURE.read_text(encoding="utf-8")
    first_data = [ln for ln in text.splitlines() if ln and not ln.startswith("Date")][0]
    # Re-parse via csv to compare mapping on a known row.
    import csv
    import io

    reader = csv.DictReader(io.StringIO(text))
    raw = next(reader)
    row = ingested.rows[0]
    assert row.cache_write == int(raw[COL_CACHE_WRITE])
    assert row.input_tokens == int(raw[COL_INPUT])
    assert row.cache_write != row.input_tokens or int(raw[COL_CACHE_WRITE]) == int(raw[COL_INPUT])
    names = {r.model for r in ingested.rows}
    assert "gemini-3.1-pro" in names
    assert any(n.startswith("cursor-grok-4.6") for n in names)


def test_unknown_column_fails_fast():
    src = FIXTURE.read_text(encoding="utf-8")
    header, rest = src.split("\n", 1)
    bad = header + ",Extra\n" + "\n".join(
        (line + "," if line else line) for line in rest.splitlines()
    )
    with pytest.raises(CsvContractError, match="colonnes inconnues"):
        parse_csv(bad)


def test_missing_column_fails_fast():
    src = FIXTURE.read_text(encoding="utf-8")
    header, rest = src.split("\n", 1)
    cols = header.split(",")
    cols.remove("Cost")
    bad = ",".join(cols) + "\n" + rest
    with pytest.raises(CsvContractError, match="colonnes manquantes"):
        parse_csv(bad)


def test_non_integer_token_fails_fast():
    src = FIXTURE.read_text(encoding="utf-8")
    lines = src.splitlines()
    # Mutate first data row output tokens
    parts = lines[1].split(",")
    parts[-2] = "12.5"
    lines[1] = ",".join(parts)
    with pytest.raises(CsvContractError, match="n'est pas un entier"):
        parse_csv("\n".join(lines) + "\n")


def test_cost_column_not_required_for_values():
    settings = Settings.model_validate_json(DEFAULTS_PATH.read_text(encoding="utf-8"))
    ingested = parse_csv(FIXTURE.read_text(encoding="utf-8"))
    assert settings.models
    assert ingested.rows
