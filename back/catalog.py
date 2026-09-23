"""Catalog import helpers shared by database initialization and tests."""

from __future__ import annotations

import csv
from pathlib import Path


LIST_FIELDS = ("categories", "languages", "event_formats", "busy_dates")
BOOLEAN_FIELDS = ("synthetic", "city_imputed", "price_imputed")


def load_csv_profiles(path: Path) -> list[dict]:
    """Load and type-check the source CSV without changing source values."""
    with path.open(encoding="utf-8-sig", newline="") as source:
        profiles = list(csv.DictReader(source))

    required = {
        "id", "anon_name", "categories", "city", "city_imputed", "synthetic",
        "price_from_kzt", "price_imputed", "event_formats", "languages",
        "max_hours", "busy_dates", "description",
    }
    if not profiles:
        raise ValueError("Каталог подрядчиков пуст.")
    missing = required - set(profiles[0])
    if missing:
        raise ValueError(f"В каталоге отсутствуют поля: {', '.join(sorted(missing))}.")

    seen: set[str] = set()
    for row_number, profile in enumerate(profiles, start=2):
        identifier = profile["id"].strip()
        if not identifier or identifier in seen:
            raise ValueError(f"Некорректный или повторяющийся ID в строке {row_number}.")
        seen.add(identifier)
        profile["id"] = identifier
        for key in LIST_FIELDS:
            profile[key] = [value for value in profile[key].split("|") if value]
        for key in BOOLEAN_FIELDS:
            if profile[key].lower() not in {"true", "false"}:
                raise ValueError(f"Поле {key} в строке {row_number} должно быть True или False.")
            profile[key] = profile[key].lower() == "true"
        profile["price_from_kzt"] = int(profile["price_from_kzt"])
        profile["max_hours"] = float(profile["max_hours"]) if profile["max_hours"] else None
        if profile["price_from_kzt"] <= 0:
            raise ValueError(f"Цена в строке {row_number} должна быть положительной.")
        if not profile["categories"] or not profile["event_formats"]:
            raise ValueError(f"В строке {row_number} нет категории или формата.")
    return profiles
