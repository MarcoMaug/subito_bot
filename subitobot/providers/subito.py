from __future__ import annotations

import logging

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


def _convenienza(price, km, anno):
    """Formula ereditata dal vecchio bot auto (subito_auto.py)."""
    if not price or not km or not anno:
        return None
    valore_effettivo = 100 / (km / 3100000) + (anno - 2000) * 175
    return round(valore_effettivo - price)


class SubitoProvider(Provider):
    """Legge gli annunci dall'URL normale di subito.it, estraendoli dal JSON
    incorporato (__NEXT_DATA__ -> initialState.items.originalList).

    L'utente configura direttamente l'URL di ricerca di subito.it con tutti i
    suoi filtri: nessun parametro API da mappare a mano."""

    def fetch(self, search: dict) -> list[Listing]:
        url = search["url"]
        category = search.get("category", "affitti")
        data = self.fetcher.get_next_data(url)
        try:
            items = data["props"]["pageProps"]["initialState"]["items"]["originalList"]
        except (KeyError, TypeError):
            logger.error("Struttura __NEXT_DATA__ inattesa per la ricerca '%s'", search.get("name"))
            return []

        listings: list[Listing] = []
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
                extra = {
                    "km": km,
                    "anno": anno,
                    "carburante": _feature(ad, "/fuel", "value"),
                    "convenienza": _convenienza(price, km, anno),
                }
            else:
                extra = {
                    "mq": _to_int(_feature(ad, "/size")),
                    "locali": _feature(ad, "/room", "value"),
                }

            listings.append(
                Listing(
                    id=_listing_id(urn),
                    title=ad.get("subject", "").strip(),
                    url=(ad.get("urls") or {}).get("default", ""),
                    category=category,
                    price=price,
                    city=city,
                    extra=extra,
                )
            )
        logger.info("Ricerca '%s': %s annunci letti", search.get("name"), len(listings))
        return listings
