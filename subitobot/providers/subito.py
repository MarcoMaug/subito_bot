from __future__ import annotations

import logging

from ..csv_export import load_recent_price_points
from ..models import Listing
from .base import Provider

logger = logging.getLogger("subitobot.subito")


def _feature(ad: dict, uri: str, field: str = "key"):
    """Estrae il primo valore di una feature dell'annuncio Subito."""
    feat = (ad.get("features") or {}).get(uri)
    if not feat:
        return None
    values = feat.get("values") or []
    return values[0].get(field) if values else None


def _to_int(value):
    try:
        return int(str(value).replace(".", "").strip())
    except (TypeError, ValueError):
        return None


def _to_float(value):
    try:
        return float(str(value).replace(".", "").replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _listing_id(urn: str) -> str:
    """Da 'id:ad:<adid>:list:<listid>' estrae <adid>, stabile tra i re-listing."""
    parts = urn.split(":")
    if len(parts) >= 3 and parts[0] == "id" and parts[1] == "ad":
        return parts[2]
    return urn


def _fit_price_model(rows: list[tuple[float, float, float]]) -> tuple[float, float, float] | None:
    """Regressione lineare (minimi quadrati) price ~ km + anno, stimata sui
    comparabili del batch corrente: niente costanti inventate, i pesi vengono
    dai dati reali degli annunci appena scaricati per questa ricerca."""
    n = len(rows)
    if n < 5:
        return None  # troppo pochi comparabili per una stima affidabile

    sum_km = sum(km for km, _, _ in rows)
    sum_anno = sum(anno for _, anno, _ in rows)
    sum_price = sum(price for _, _, price in rows)
    sum_km2 = sum(km * km for km, _, _ in rows)
    sum_anno2 = sum(anno * anno for _, anno, _ in rows)
    sum_km_anno = sum(km * anno for km, anno, _ in rows)
    sum_km_price = sum(km * price for km, _, price in rows)
    sum_anno_price = sum(anno * price for _, anno, price in rows)

    # Sistema normale X^T X b = X^T y per price = b0 + b1*km + b2*anno
    system = [
        [float(n), sum_km, sum_anno, sum_price],
        [sum_km, sum_km2, sum_km_anno, sum_km_price],
        [sum_anno, sum_km_anno, sum_anno2, sum_anno_price],
    ]
    return _solve_3x3(system)


def _solve_3x3(a: list[list[float]]) -> tuple[float, float, float] | None:
    """Eliminazione gaussiana con pivot parziale su un sistema 3x3 aumentato."""
    for col in range(3):
        pivot_row = max(range(col, 3), key=lambda r: abs(a[r][col]))
        if abs(a[pivot_row][col]) < 1e-9:
            return None  # sistema singolare (es. tutti gli annunci con lo stesso anno)
        a[col], a[pivot_row] = a[pivot_row], a[col]
        for r in range(3):
            if r == col:
                continue
            factor = a[r][col] / a[col][col]
            for c in range(col, 4):
                a[r][c] -= factor * a[col][c]
    return (a[0][3] / a[0][0], a[1][3] / a[1][1], a[2][3] / a[2][2])


def _convenienza(model: tuple[float, float, float] | None, price, km, anno):
    """Indice di convenienza: quanto l'annuncio è sotto il prezzo previsto dal
    modello per quel km/anno. Non scende mai sotto 0 (0 = non conveniente)."""
    if model is None or not price or not km or not anno:
        return None
    b0, b1, b2 = model
    prezzo_previsto = b0 + b1 * km + b2 * anno
    return round(max(0.0, prezzo_previsto - price))


class SubitoProvider(Provider):
    """Legge gli annunci dall'URL normale di subito.it, estraendoli dal JSON
    incorporato (__NEXT_DATA__ -> initialState.items.originalList).

    L'utente configura direttamente l'URL di ricerca di subito.it con tutti i
    suoi filtri: nessun parametro API da mappare a mano."""

    def fetch(self, search: dict) -> list[Listing]:
        url = search["url"]
        category = search.get("category", "affitti")
        data = self.fetcher.get_next_data(url, proxy=search.get("proxy"))
        try:
            items = data["props"]["pageProps"]["initialState"]["items"]["originalList"]
        except (KeyError, TypeError):
            logger.error("Struttura __NEXT_DATA__ inattesa per la ricerca '%s'", search.get("name"))
            return []

        raw: list[dict] = []
        for ad in items:
            if ad.get("kind") != "AdItem":
                continue  # salta banner/annunci sponsorizzati non-standard
            urn = ad.get("urn")
            if not urn:
                continue
            geo = ad.get("geo") or {}
            city = (geo.get("town") or {}).get("value") or (geo.get("city") or {}).get("value")
            price = _to_float(_feature(ad, "/price"))

            if category == "auto":
                km = _to_int(_feature(ad, "/mileage_scalar"))
                anno = _to_int(_feature(ad, "/year"))
                fields = {"km": km, "anno": anno, "carburante": _feature(ad, "/fuel", "value")}
            else:
                fields = {"mq": _to_int(_feature(ad, "/size")), "locali": _feature(ad, "/room", "value")}

            raw.append(
                {
                    "id": _listing_id(urn),
                    "title": ad.get("subject", "").strip(),
                    "url": (ad.get("urls") or {}).get("default", ""),
                    "price": price,
                    "city": city,
                    "fields": fields,
                }
            )

        model = None
        if category == "auto":
            comparabili = [
                (r["fields"]["km"], r["fields"]["anno"], r["price"])
                for r in raw
                if r["price"] and r["fields"]["km"] and r["fields"]["anno"]
            ]
            # Storico dal csv (stessa ricerca, ultimi 6 mesi) come comparabili
            # aggiuntivi: se manca il csv o i dati sono troppo vecchi, la lista
            # torna vuota e la stima resta basata solo sul batch corrente.
            comparabili += load_recent_price_points("auto", search.get("name"), months=6)
            model = _fit_price_model(comparabili)

        listings: list[Listing] = []
        for r in raw:
            extra = dict(r["fields"])
            if category == "auto":
                extra["convenienza"] = _convenienza(model, r["price"], r["fields"]["km"], r["fields"]["anno"])
            listings.append(
                Listing(
                    id=r["id"],
                    title=r["title"],
                    url=r["url"],
                    category=category,
                    price=r["price"],
                    city=r["city"],
                    extra=extra,
                )
            )
        logger.info("Ricerca '%s': %s annunci letti", search.get("name"), len(listings))
        return listings
