from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone

FIELDNAMES = ["first_seen", "search_name", "id", "title", "url", "price", "city", "extra"]

_PATHS = {"auto": "auto.csv", "affitti": "affitti.csv"}


def append_listings(search_name: str, category: str, listings) -> None:
    """Accoda gli annunci nuovi al csv della categoria (auto.csv / affitti.csv)."""
    path = _PATHS.get(category)
    if not listings or path is None:
        return

    file_exists = os.path.isfile(path)
    now = datetime.now(timezone.utc).isoformat()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for listing in listings:
            writer.writerow(
                {
                    "first_seen": now,
                    "search_name": search_name,
                    "id": listing.id,
                    "title": listing.title,
                    "url": listing.url,
                    "price": listing.price,
                    "city": listing.city,
                    "extra": json.dumps(listing.extra, ensure_ascii=False),
                }
            )


def load_recent_price_points(category: str, search_name: str, months: int = 6) -> list[tuple[float, float, float]]:
    """Legge dal csv (se esiste) gli annunci della stessa ricerca con first_seen
    negli ultimi `months` mesi, come comparabili storici per la stima del
    valore. Righe senza csv, senza km/anno o troppo vecchie vengono ignorate:
    se non resta nulla, il chiamante ricade sui soli annunci del batch."""
    path = _PATHS.get(category)
    if path is None or not os.path.isfile(path):
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)
    points: list[tuple[float, float, float]] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("search_name") != search_name:
                continue
            try:
                first_seen = datetime.fromisoformat(row["first_seen"])
            except (KeyError, ValueError):
                continue
            if first_seen < cutoff:
                continue
            try:
                price = float(row["price"])
            except (TypeError, ValueError):
                continue
            try:
                extra = json.loads(row.get("extra") or "{}")
            except json.JSONDecodeError:
                continue
            km, anno = extra.get("km"), extra.get("anno")
            if km and anno:
                points.append((float(km), float(anno), price))
    return points
