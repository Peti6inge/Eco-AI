from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from math import erf, sqrt
from typing import Literal, Sequence

import numpy as np

from app.csv_ingest import UsageRow, match_model
from app.schema import ModelConfig, Settings

N_DRAWS = 20_000
OMIT_TOKEN_SHARE = 0.01
CDF_POINTS = 800

Metric = Literal["co2", "water"]


def product_moments(
    mu_x: float, sigma_x: float, mu_y: float, sigma_y: float
) -> tuple[float, float]:
    """Moments de Z = X Y pour X, Y indépendants (non gaussiens)."""
    mean = mu_x * mu_y
    var = (
        mu_x**2 * sigma_y**2
        + mu_y**2 * sigma_x**2
        + sigma_x**2 * sigma_y**2
    )
    return mean, float(sqrt(var))


def exact_usd(row: UsageRow, model: ModelConfig) -> float:
    return (
        row.input_tokens * model.input
        + row.output * model.output
        + row.cache_read * model.cache_read
        + row.cache_write * model.cache_write
    )


def _truncated_normal(
    rng: np.random.Generator, mu: float, sigma: float, size: int
) -> np.ndarray:
    if sigma <= 0:
        return np.full(size, max(mu, 1e-12), dtype=float)
    samples = rng.normal(mu, sigma, size)
    for _ in range(32):
        bad = samples <= 0
        if not np.any(bad):
            break
        samples[bad] = rng.normal(mu, sigma, int(bad.sum()))
    return np.maximum(samples, 1e-12)


def _norm_cdf(x: np.ndarray, mean: float, std: float) -> np.ndarray:
    if std <= 0:
        return (x >= mean).astype(float)
    z = (x - mean) / (std * sqrt(2.0))
    return 0.5 * (1.0 + np.vectorize(erf)(z))


@dataclass
class EstimateResult:
    coverage_pct: float
    omitted: list[dict]
    quartiles: dict[str, float]
    cdf: dict[str, list[float]]
    gaussian_overlay: dict[str, list[float]]
    unit: str
    n_draws: int
    date_min: date | None
    date_max: date | None
    skipped_empty: int
    total_cost_usd: float
    mean: float
    std: float
    configured_model_ids: list[str]
    rows_used: int


def estimate(
    rows: Sequence[UsageRow],
    settings: Settings,
    *,
    metric: Metric = "co2",
    graph_model_ids: Sequence[str] | None = None,
    skipped_empty: int = 0,
    date_min: date | None = None,
    date_max: date | None = None,
    n_draws: int = N_DRAWS,
    rng: np.random.Generator | None = None,
) -> EstimateResult:
    models = settings.models
    providers = settings.provider_by_id()
    configured_ids = [m.id for m in models]
    graph_set = set(graph_model_ids) if graph_model_ids is not None else set(configured_ids)

    total_tokens = sum(r.total_tokens for r in rows)
    covered_tokens = 0
    omitted_tokens: dict[str, int] = defaultdict(int)
    usd_by_model: dict[str, float] = defaultdict(float)

    for row in rows:
        matched = match_model(row.model, models)
        if matched is None:
            omitted_tokens[row.model] += row.total_tokens
            continue
        covered_tokens += row.total_tokens
        usd_by_model[matched.id] += exact_usd(row, matched)

    coverage_pct = (100.0 * covered_tokens / total_tokens) if total_tokens else 0.0
    omitted = [
        {"model": name, "tokens": tokens}
        for name, tokens in sorted(omitted_tokens.items(), key=lambda kv: (-kv[1], kv[0]))
        if total_tokens and tokens / total_tokens >= OMIT_TOKEN_SHARE
    ]

    graph_models = [m for m in models if m.id in graph_set]
    total_cost = float(sum(usd_by_model[m.id] for m in graph_models))

    rng = rng or np.random.default_rng()
    provider_ids = sorted({m.provider_id for m in graph_models})
    intensity = {}
    for pid in provider_ids:
        provider = providers.get(pid)
        if provider is None:
            raise ValueError(f"Fournisseur inconnu pour un modèle : {pid}")
        if metric == "co2":
            mu, sigma = provider.mu_kg_per_kWh, provider.sigma_kg_per_kWh
        else:
            mu, sigma = provider.mu_L_per_kWh, provider.sigma_L_per_kWh
        intensity[pid] = _truncated_normal(rng, mu, sigma, n_draws)

    footprint = np.zeros(n_draws, dtype=float)
    for model in graph_models:
        usd = usd_by_model.get(model.id, 0.0)
        if usd == 0:
            continue
        energy = _truncated_normal(rng, model.mu_kWh_per_usd, model.sigma_kWh_per_usd, n_draws)
        footprint += usd * energy * intensity[model.provider_id]

    q1, median, q3 = np.percentile(footprint, [25, 50, 75])
    order = np.argsort(footprint)
    sorted_f = footprint[order]
    idx = np.unique(np.linspace(0, n_draws - 1, CDF_POINTS, dtype=int))
    cdf_x = sorted_f[idx].tolist()
    cdf_y = ((idx + 1) / n_draws).tolist()

    mean = float(footprint.mean())
    std = float(footprint.std(ddof=0))
    gx = np.linspace(float(sorted_f[0]), float(sorted_f[-1]), 400)
    gy = _norm_cdf(gx, mean, std)

    unit = "kg CO₂" if metric == "co2" else "L eau"
    return EstimateResult(
        coverage_pct=coverage_pct,
        omitted=omitted,
        quartiles={"q1": float(q1), "median": float(median), "q3": float(q3)},
        cdf={"x": cdf_x, "y": cdf_y},
        gaussian_overlay={"x": gx.tolist(), "y": gy.tolist()},
        unit=unit,
        n_draws=n_draws,
        date_min=date_min,
        date_max=date_max,
        skipped_empty=skipped_empty,
        total_cost_usd=total_cost,
        mean=mean,
        std=std,
        configured_model_ids=configured_ids,
        rows_used=len(rows),
    )
