from __future__ import annotations

import logging
import re

from ..models import Listing
from .base import Provider

logger = logging.getLogger("subitobot.immobiliare")

HOME = "https://www.immobiliare.it/"


def _find_results(next_data: dict) -> list:
    """Trova la lista 'results' dentro dehydratedState.queries, senza dipendere
    dall'indice esatto della query."""
    try:
        queries = next_data["props"]["pageProps"]["dehydratedState"]["queries"]
    except (KeyError, TypeError):
        return []
    for q in queries:
        data = (q.get("state") or {}).get("data") or {}
        results = data.get("results")
        if isinstance(results, list) and results and "realEstate" in results[0]:
            return results
    return []


def _surface_to_int(value):
    if not value:
        return None
    m = re.search(r"\d+", str(value).replace(".", ""))
    return int(m.group()) if m else None


def _search_urls(search: dict) -> list[str]:
    """Immobiliare non permette di disegnare una zona di ricerca personalizzata:
    per coprire una zona irregolare si configurano più URL (una per sotto-zona)
    tramite il campo 'urls', in alternativa al singolo 'url'."""
    urls = search.get("urls")
    return list(urls) if urls else [search["url"]]


class ImmobiliareProvider(Provider):
    """Affitti da immobiliare.it. Gli annunci sono nel JSON incorporato nella
    pagina (__NEXT_DATA__ -> dehydratedState). L'utente configura l'URL normale
    di ricerca del sito (o più URL, per coprire zone che il sito non permette
    di disegnare in un'unica ricerca)."""

    def fetch(self, search: dict) -> list[Listing]:
        seen_ids: set[str] = set()
        listings: list[Listing] = []
        for url in _search_urls(search):
            data = self.fetcher.get_next_data(url, warmup=HOME, proxy=search.get("proxy"))
            results = _find_results(data)
            if not results:
                logger.error("Nessun risultato in __NEXT_DATA__ per '%s' (%s)", search.get("name"), url)
                continue
            for res in results:
                re_ = res.get("realEstate") or {}
                rid = re_.get("id")
                if not rid or str(rid) in seen_ids:
                    continue
                seen_ids.add(str(rid))
                price = (re_.get("price") or {}).get("value")
                prop = (re_.get("properties") or [{}])[0]
                loc = prop.get("location") or {}
                city = loc.get("city") or loc.get("province")
                listings.append(
                    Listing(
                        id=str(rid),
                        title=(re_.get("title") or "").strip(),
                        url=(res.get("seo") or {}).get("url", ""),
                        category="affitti",
                        price=float(price) if price is not None else None,
                        city=city,
                        extra={
                            "mq": _surface_to_int(prop.get("surface")),
                            "locali": prop.get("rooms"),
                        },
                    )
                )
        logger.info("Ricerca '%s': %s annunci letti", search.get("name"), len(listings))
        return listings
