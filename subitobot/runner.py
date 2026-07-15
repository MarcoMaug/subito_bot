from __future__ import annotations

import logging
import time

from .fetcher import Fetcher, FetchError
from .notifier import TelegramNotifier
from .providers import get_provider
from .store import Store

logger = logging.getLogger("subitobot.runner")


def _passes_filters(listing, filters: dict) -> bool:
    """Filtri opzionali applicati prima di notificare (l'annuncio resta comunque
    marcato come 'visto' per non ri-notificarlo)."""
    conv_min = filters.get("convenienza_min")
    if conv_min is not None:
        conv = listing.extra.get("convenienza")
        if conv is None or conv < conv_min:
            return False
    price_max = filters.get("price_max")
    if price_max is not None and listing.price is not None and listing.price > price_max:
        return False
    return True


def run_search(search: dict, fetcher: Fetcher, store: Store, notifier: TelegramNotifier) -> None:
    name = search["name"]
    provider = get_provider(search["provider"], fetcher)
    listings = provider.fetch(search)
    if not listings:
        return

    known = store.known_ids(name)
    is_seed = store.count(name) == 0
    new = [l for l in listings if l.id not in known]

    if is_seed:
        # Primo giro: registra tutto senza notificare, per non spammare gli annunci esistenti.
        store.add_many(name, [l.id for l in listings])
        logger.info("Ricerca '%s': seed iniziale, %s annunci registrati (nessuna notifica).", name, len(listings))
        return

    filters = search.get("filters") or {}
    notified = 0
    for listing in new:
        if _passes_filters(listing, filters):
            if notifier.notify(listing):
                notified += 1

    # Registra tutti i nuovi (anche quelli filtrati) per non riconsiderarli.
    store.add_many(name, [l.id for l in new])
    logger.info("Ricerca '%s': %s nuovi, %s notificati.", name, len(new), notified)


def run_once(cfg: dict, fetcher: Fetcher, store: Store, notifier: TelegramNotifier) -> None:
    for search in cfg["searches"]:
        try:
            run_search(search, fetcher, store, notifier)
        except FetchError as exc:
            logger.warning("Ricerca '%s' saltata (download): %s", search.get("name"), exc)
        except Exception:
            logger.exception("Errore inatteso nella ricerca '%s'", search.get("name"))


def run_loop(cfg: dict, fetcher: Fetcher, store: Store, notifier: TelegramNotifier) -> None:
    poll = cfg["poll_seconds"]
    logger.info("Avvio loop: %s ricerche, ogni %s secondi.", len(cfg["searches"]), poll)
    while True:
        run_once(cfg, fetcher, store, notifier)
        time.sleep(poll)
