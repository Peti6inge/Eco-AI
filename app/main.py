from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.csv_ingest import CsvContractError, filter_period, parse_csv
from app.estimate import estimate
from app.schema import Settings
from app.settings_store import load_settings, save_settings

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Eco-AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/settings")
def get_settings() -> dict:
    return load_settings().model_dump()


@app.put("/api/settings")
def put_settings(payload: Settings) -> dict:
    try:
        return save_settings(payload).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    metric: str = Form("co2"),
    date_from: str | None = Form(None),
    date_to: str | None = Form(None),
    model_ids: str | None = Form(None),
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
    settings = load_settings()
    ids = None
    if model_ids:
        ids = [s.strip() for s in model_ids.split(",") if s.strip()]

    result = estimate(
        rows,
        settings,
        metric=metric,  # type: ignore[arg-type]
        graph_model_ids=ids,
        skipped_empty=ingested.skipped_empty,
        date_min=ingested.date_min,
        date_max=ingested.date_max,
    )
    return {
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
    }


def _parse_iso_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Date invalide : {value}") from exc
