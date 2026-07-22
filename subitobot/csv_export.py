from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone

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
