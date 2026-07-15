from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Listing:
    """Annuncio normalizzato, comune a tutti i provider."""

    id: str  # id stabile dell'annuncio (per dedup)
    title: str
    url: str
    category: str  # "auto" | "affitti"
    price: float | None = None
    city: str | None = None
    extra: dict = field(default_factory=dict)  # km, anno, fuel, mq, locali, convenienza...
