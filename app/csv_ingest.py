from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

from app.schema import ModelConfig

REQUIRED_HEADERS = (
    "Date",
    "Cloud Agent ID",
    "Automation ID",
    "Kind",
    "Model",
    "Max Mode",
    "Input (w/ Cache Write)",
    "Input (w/o Cache Write)",
    "Cache Read",
    "Output Tokens",
    "Total Tokens",
    "Cost",
)

# Export Cursor : libellés inversés par rapport au métier (contrat V1 figé).
COL_CACHE_WRITE = "Input (w/ Cache Write)"
COL_INPUT = "Input (w/o Cache Write)"
COL_CACHE_READ = "Cache Read"
COL_OUTPUT = "Output Tokens"
COL_TOTAL = "Total Tokens"

TOKEN_COLUMNS = (COL_CACHE_WRITE, COL_INPUT, COL_CACHE_READ, COL_OUTPUT, COL_TOTAL)

_INT_RE = re.compile(r"-?\d+")


class CsvContractError(ValueError):
    """Schéma CSV invalide — pas d'estimation partielle."""


@dataclass(frozen=True)
class UsageRow:
    date: datetime | None
    model: str
    cache_write: int
    input_tokens: int
    cache_read: int
    output: int
    total_tokens: int


@dataclass(frozen=True)
class IngestResult:
    rows: list[UsageRow]
    skipped_empty: int
    date_min: date | None
    date_max: date | None


def _parse_int_token(value: str | None, column: str, line_no: int) -> int | None:
    text = (value or "").strip()
    if text == "":
        return None
    if not _INT_RE.fullmatch(text):
        raise CsvContractError(
            f"Ligne {line_no} : la colonne « {column} » n'est pas un entier "
            f"(valeur {value!r})."
        )
    return int(text)


def _parse_date(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise CsvContractError(f"Date illisible : {value!r}") from exc


def match_model(csv_model: str, models: Sequence[ModelConfig]) -> ModelConfig | None:
    """Préfixe le plus long parmi tous les `match_prefixes` configurés."""
    best: ModelConfig | None = None
    best_len = -1
    name = csv_model.strip()
    for model in models:
        for prefix in model.match_prefixes:
            if name.startswith(prefix) and len(prefix) > best_len:
                best = model
                best_len = len(prefix)
    return best


def parse_csv(text: str) -> IngestResult:
    stream = io.StringIO(text)
    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        raise CsvContractError("CSV sans en-tête.")
    headers = [h.strip() for h in reader.fieldnames if h is not None]
    if any(h is None or h == "" for h in reader.fieldnames):
        raise CsvContractError("Une colonne sans nom est présente.")
    header_set = set(headers)
    required = set(REQUIRED_HEADERS)
    if header_set != required:
        missing = sorted(required - header_set)
        extra = sorted(header_set - required)
        parts: list[str] = []
        if missing:
            parts.append("colonnes manquantes : " + ", ".join(missing))
        if extra:
            parts.append("colonnes inconnues : " + ", ".join(extra))
        raise CsvContractError(
            "Contrat CSV Cursor non respecté (" + " ; ".join(parts) + ")."
        )
    if len(headers) != len(REQUIRED_HEADERS):
        raise CsvContractError("En-têtes dupliqués.")

    rows: list[UsageRow] = []
    skipped_empty = 0
    for i, raw in enumerate(reader, start=2):
        tokens = {col: _parse_int_token(raw.get(col), col, i) for col in TOKEN_COLUMNS}
        if all(v is None for v in tokens.values()):
            skipped_empty += 1
            continue
        cache_write = tokens[COL_CACHE_WRITE] or 0
        input_tokens = tokens[COL_INPUT] or 0
        cache_read = tokens[COL_CACHE_READ] or 0
        output = tokens[COL_OUTPUT] or 0
        total = tokens[COL_TOTAL]
        if total is None:
            total = cache_write + input_tokens + cache_read + output
        model = (raw.get("Model") or "").strip()
        if not model:
            raise CsvContractError(f"Ligne {i} : modèle vide alors que des tokens sont présents.")
        when = _parse_date(raw.get("Date"))
        rows.append(
            UsageRow(
                date=when,
                model=model,
                cache_write=cache_write,
                input_tokens=input_tokens,
                cache_read=cache_read,
                output=output,
                total_tokens=total,
            )
        )

    dates = [r.date.date() for r in rows if r.date is not None]
    return IngestResult(
        rows=rows,
        skipped_empty=skipped_empty,
        date_min=min(dates) if dates else None,
        date_max=max(dates) if dates else None,
    )


def filter_period(
    rows: Sequence[UsageRow],
    date_from: date | None,
    date_to: date | None,
) -> list[UsageRow]:
    out: list[UsageRow] = []
    for row in rows:
        if row.date is None:
            if date_from is None and date_to is None:
                out.append(row)
            continue
        d = row.date.date()
        if date_from is not None and d < date_from:
            continue
        if date_to is not None and d > date_to:
            continue
        out.append(row)
    return list(out)
