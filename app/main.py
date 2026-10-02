from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.csv_ingest import CsvContractError, filter_period, parse_csv
from app.estimate import estimate
from app.schema import Settings
from app.settings_store import (
    InvalidPackError,
    UnknownPackError,
    default_pack,
    list_packs,
    load_all_settings,
    load_settings,
    save_settings,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Eco-AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/settings")
def get_settings(pack: str | None = Query(None)) -> dict:
    try:
        packs = list_packs()
        chosen = pack or default_pack()
        settings = load_settings(chosen)
    except InvalidPackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnknownPackError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "pack": chosen,
        "packs": packs,
        "settings": settings.model_dump(),
    }


@app.put("/api/settings")
def put_settings(payload: Settings, pack: str | None = Query(None)) -> dict:
    try:
        chosen = pack or default_pack()
        saved = save_settings(payload, chosen)
    except InvalidPackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnknownPackError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    return {
        "pack": chosen,
        "packs": list_packs(),
        "settings": saved.model_dump(),
    }


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    metric: str = Form("co2"),
    date_from: str | None = Form(None),
    date_to: str | None = Form(None),
    model_ids: str | None = Form(None),
    pack: str | None = Form(None),
) -> dict:
    if metric not in {"co2", "water"}:
        raise HTTPException(status_code=400, detail="metric doit être co2 ou water.")
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Le fichier n'est pas du UTF-8.") from exc
    try:
        ingested = parse_csv(text)
    except CsvContractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    start = _parse_iso_date(date_from)
    end = _parse_iso_date(date_to)
    rows = filter_period(ingested.rows, start, end)
    try:
        chosen = pack or default_pack()
        settings = load_settings(chosen)
    except InvalidPackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnknownPackError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    ids = None
    if model_ids:
        ids = [s.strip() for s in model_ids.split(",") if s.strip()]

    try:
        result = estimate(
            rows,
            settings,
            metric=metric,  # type: ignore[arg-type]
            graph_model_ids=ids,
            skipped_empty=ingested.skipped_empty,
            date_min=ingested.date_min,
            date_max=ingested.date_max,
        )
        comparison = _compare_packs(rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "pack": chosen,
        "coverage_pct": result.coverage_pct,
        "omitted": result.omitted,
        "quartiles": result.quartiles,
        "cdf": result.cdf,
        "gaussian_overlay": result.gaussian_overlay,
        "unit": result.unit,
        "n_draws": result.n_draws,
        "date_min": result.date_min.isoformat() if result.date_min else None,
        "date_max": result.date_max.isoformat() if result.date_max else None,
        "skipped_empty": result.skipped_empty,
        "total_cost_usd": result.total_cost_usd,
        "mean": result.mean,
        "std": result.std,
        "configured_model_ids": result.configured_model_ids,
        "rows_used": result.rows_used,
        "comparison": comparison,
    }


def _compare_packs(rows, n_draws: int | None = None) -> list[dict]:
    extra = {"include_distribution": False}
    if n_draws is not None:
        extra["n_draws"] = n_draws
    out: list[dict] = []
    for pack_id, settings in load_all_settings():
        co2 = estimate(rows, settings, metric="co2", **extra)
        water = estimate(rows, settings, metric="water", **extra)
        out.append(
            {
                "pack": pack_id,
                "coverage_pct": co2.coverage_pct,
                "co2": co2.quartiles,
                "water": water.quartiles,
            }
        )
    return out


def _parse_iso_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    text = value.strip()
    if len(text) != 10:
        raise HTTPException(
            status_code=400,
            detail="Date invalide : format AAAA-MM-JJ exigé.",
        )
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Date invalide : {value}") from exc
