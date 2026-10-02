from __future__ import annotations

from datetime import date

import numpy as np

from app.csv_ingest import filter_period, parse_csv
from app.estimate import exact_usd, estimate
from app.schema import ModelConfig, Settings
from app.settings_store import DEFAULTS_PATH
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "usage-events-2026-10-02__2__43a7.csv"


def test_cost_uses_configured_prices_not_csv_cost_column():
    model = ModelConfig(
        id="x",
        provider_id="spacexai",
        match_prefixes=["x"],
        input=2.0,
        output=3.0,
        cache_read=4.0,
        cache_write=5.0,
        mu_kWh_per_usd=0.1,
        sigma_kWh_per_usd=0.01,
    )
    ingested = parse_csv(
        "Date,Cloud Agent ID,Automation ID,Kind,Model,Max Mode,"
        "Input (w/ Cache Write),Input (w/o Cache Write),Cache Read,"
        "Output Tokens,Total Tokens,Cost\n"
        "2026-10-02,,,,x,false,1,2,3,4,10,Included\n"
    )
    row = ingested.rows[0]
    assert exact_usd(row, model) == 2 * 2.0 + 4 * 3.0 + 3 * 4.0 + 1 * 5.0


def test_coverage_and_omitted_independent_of_graph_toggles():
    settings = Settings.model_validate_json(DEFAULTS_PATH.read_text(encoding="utf-8"))
    ingested = parse_csv(FIXTURE.read_text(encoding="utf-8"))
    full = estimate(
        ingested.rows,
        settings,
        metric="co2",
        skipped_empty=ingested.skipped_empty,
        date_min=ingested.date_min,
        date_max=ingested.date_max,
        n_draws=2000,
        rng=np.random.default_rng(0),
    )
    subset = estimate(
        ingested.rows,
        settings,
        metric="co2",
        graph_model_ids=["auto"],
        n_draws=2000,
        rng=np.random.default_rng(0),
    )
    assert full.coverage_pct == subset.coverage_pct
    assert full.omitted == subset.omitted
    assert full.coverage_pct < 80
    assert any(item["model"].startswith("gpt-5.6") for item in full.omitted)
    assert not any(item["model"].startswith("gemini") for item in full.omitted)


def test_period_filter_shrinks_rows():
    ingested = parse_csv(FIXTURE.read_text(encoding="utf-8"))
    only_day2 = filter_period(ingested.rows, date(2026, 10, 2), date(2026, 10, 2))
    assert 0 < len(only_day2) < len(ingested.rows)
