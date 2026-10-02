from __future__ import annotations

import csv
import random
from pathlib import Path

HEADERS = [
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
]

# Mix volontaire : une grande part des tokens hors seed V1 (gemini, gpt-5.6).
WEIGHTED_MODELS = [
    ("gemini-3.1-pro", 48),
    ("gpt-5.6-high", 22),
    ("gpt-5.6-low", 14),
    ("cursor-grok-4.6-medium", 18),
    ("cursor-grok-4.6-high-fast", 12),
    ("claude-opus-5-5-high", 16),
    ("claude-4.6-sonnet-medium", 10),
    ("composer-2.5-fast", 8),
    ("composer-2.5", 6),
    ("grok-4.7-medium", 8),
    ("auto", 5),
]


def _expand() -> list[str]:
    names: list[str] = []
    for name, n in WEIGHTED_MODELS:
        names.extend([name] * n)
    return names


def main() -> None:
    rng = random.Random(42)
    names = _expand()
    rng.shuffle(names)
    # 223 lignes utiles + 2 lignes tokens vides
    while len(names) < 223:
        names.append(rng.choice([m for m, _ in WEIGHTED_MODELS]))
    names = names[:223]

    out = Path(__file__).resolve().parent / "usage-events-2026-10-02__2__43a7.csv"
    rows: list[dict[str, str]] = []
    for i, model in enumerate(names):
        hour = 8 + (i % 14)
        minute = (i * 7) % 60
        day = 1 + (i % 2)
        cache_write = rng.randint(0, 4000)
        inp = rng.randint(200, 18000)
        cache_read = rng.randint(0, 12000)
        output = rng.randint(50, 2500)
        total = cache_write + inp + cache_read + output
        # gonfler gemini/gpt pour rendre le % d'omis visible
        if model.startswith("gemini") or model.startswith("gpt-"):
            inp *= 4
            cache_read *= 3
            total = cache_write + inp + cache_read + output
        rows.append(
            {
                "Date": f"2026-10-0{day}T{hour:02d}:{minute:02d}:00.000Z",
                "Cloud Agent ID": "" if i % 5 else f"bc-{i:04d}",
                "Automation ID": "",
                "Kind": rng.choice(["Chat", "Edit", "Agent"]),
                "Model": model,
                "Max Mode": "true" if i % 9 == 0 else "false",
                "Input (w/ Cache Write)": str(cache_write),
                "Input (w/o Cache Write)": str(inp),
                "Cache Read": str(cache_read),
                "Output Tokens": str(output),
                "Total Tokens": str(total),
                "Cost": rng.choice(["Included", "Free"]),
            }
        )
    empty = {
        "Date": "2026-10-02T00:00:00.000Z",
        "Cloud Agent ID": "",
        "Automation ID": "",
        "Kind": "",
        "Model": "",
        "Max Mode": "",
        "Input (w/ Cache Write)": "",
        "Input (w/o Cache Write)": "",
        "Cache Read": "",
        "Output Tokens": "",
        "Total Tokens": "",
        "Cost": "",
    }
    rows.append(empty)
    rows.append(dict(empty))

    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out} ({len(rows)} data rows)")


if __name__ == "__main__":
    main()
