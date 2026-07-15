from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class Store:
    """Persistenza degli annunci già visti, per (search_name, listing_id).

    Il dedup avviene sull'id stabile dell'annuncio: un annuncio è "nuovo"
    solo se il suo id non è ancora stato registrato per quella ricerca.
    """

    def __init__(self, path: str = "seen.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen (
                search_name TEXT NOT NULL,
                listing_id  TEXT NOT NULL,
                first_seen  TEXT NOT NULL,
                PRIMARY KEY (search_name, listing_id)
            )
            """
        )
        self.conn.commit()

    def known_ids(self, search_name: str) -> set[str]:
        rows = self.conn.execute(
            "SELECT listing_id FROM seen WHERE search_name = ?", (search_name,)
        ).fetchall()
        return {r[0] for r in rows}

    def count(self, search_name: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM seen WHERE search_name = ?", (search_name,)
        ).fetchone()
        return row[0]

    def add_many(self, search_name: str, listing_ids) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.executemany(
            "INSERT OR IGNORE INTO seen (search_name, listing_id, first_seen) VALUES (?, ?, ?)",
            [(search_name, lid, now) for lid in listing_ids],
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
