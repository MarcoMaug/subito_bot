from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from ..models import Listing
from .base import Provider

logger = logging.getLogger("subitobot.idealista")

HOME = "https://www.idealista.it/"
_ID_RE = re.compile(r"/(?:immobile|annuncio)?/?(\d+)/?$|/(\d+)/")


def _listing_id(href: str) -> str | None:
    m = re.search(r"(\d+)", href or "")
    return m.group(1) if m else None


def _price_to_float(text):
    if not text:
        return None
    m = re.search(r"[\d.]+", text.replace("\xa0", ""))
    return float(m.group().replace(".", "")) if m else None


def _first_int(candidates):
    """Primo intero trovato tra stringhe tipo '80 m²' o '3 locali'."""
    for c in candidates:
        m = re.search(r"\d+", c.replace(".", ""))
        if m:
            return int(m.group())
    return None


class IdealistaProvider(Provider):
    """Affitti da idealista.it (HTML). Il sito usa DataDome: si scarica con una
    sessione nuova + warm-up sulla homepage (vedi Fetcher.get_fresh)."""

    def fetch(self, search: dict) -> list[Listing]:
        url = search["url"]
        resp = self.fetcher.get_fresh(url, warmup=HOME, proxy=search.get("proxy"))
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("article", class_="item")

        listings: list[Listing] = []
        for art in articles:
            link = art.find("a", class_="item-link")
            if not link:
                continue
            href = link.get("href", "")
            lid = _listing_id(href)
            if not lid:
                continue
            title = (link.get("title") or link.get_text(strip=True)).strip()
            price_el = art.find("span", class_="item-price")
            details = [d.get_text(" ", strip=True) for d in art.find_all("span", class_="item-detail")]
            mq = _first_int(d for d in details if "m²" in d or "m2" in d)
            locali = _first_int(d for d in details if "local" in d.lower())
            city = title.split(",")[-1].strip() if "," in title else None

            listings.append(
                Listing(
                    id=lid,
                    title=title,
                    url=href if href.startswith("http") else f"https://www.idealista.it{href}",
                    category="affitti",
                    price=_price_to_float(price_el.get_text(strip=True) if price_el else None),
                    city=city,
                    extra={"mq": mq, "locali": locali},
                )
            )
        logger.info("Ricerca '%s': %s annunci letti", search.get("name"), len(listings))
        return listings
