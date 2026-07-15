from __future__ import annotations

import json
import logging
import re
import time

from curl_cffi import requests as creq

logger = logging.getLogger("subitobot.fetcher")

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)

# Impersonare il TLS di Chrome è ciò che permette di superare Akamai/DataDome:
# requests/curl "normali" vengono bloccati con 403 Access Denied.
IMPERSONATE = "chrome124"


class FetchError(Exception):
    """Errore di download non recuperabile per questo ciclo (es. 403 persistente)."""


class Fetcher:
    """Client HTTP che impersona Chrome, con sessione riusata e retry.

    La sessione mantiene i cookie del challenge anti-bot tra le richieste,
    riducendo i blocchi nei cicli successivi.
    """

    DEFAULT_HEADERS = {
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, timeout: int = 25, retries: int = 3, backoff: float = 2.0):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.session = self._new_session()

    def _new_session(self):
        session = creq.Session(impersonate=IMPERSONATE)
        session.headers.update(self.DEFAULT_HEADERS)
        return session

    def get(self, url: str, **kwargs):
        """GET con retry esponenziale. Rilancia FetchError se esaurisce i tentativi."""
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout, **kwargs)
                if resp.status_code == 200:
                    return resp
                logger.warning("GET %s -> HTTP %s (tentativo %s/%s)", url, resp.status_code, attempt, self.retries)
                last_exc = FetchError(f"HTTP {resp.status_code} su {url}")
            except Exception as exc:  # errori di rete/timeout
                logger.warning("GET %s errore: %r (tentativo %s/%s)", url, exc, attempt, self.retries)
                last_exc = exc
            if attempt < self.retries:
                time.sleep(self.backoff * attempt)
        raise FetchError(str(last_exc))

    def get_next_data(self, url: str) -> dict:
        """Scarica una pagina e restituisce il JSON incorporato in __NEXT_DATA__."""
        resp = self.get(url)
        match = _NEXT_DATA_RE.search(resp.text)
        if not match:
            raise FetchError(f"__NEXT_DATA__ non trovato in {url}")
        return json.loads(match.group(1))

    def get_json(self, url: str, **kwargs) -> dict:
        resp = self.get(url, **kwargs)
        return resp.json()

    def get_fresh(self, url: str, warmup: str | None = None, headers: dict | None = None):
        """GET usando una sessione NUOVA a ogni tentativo, con eventuale warm-up.

        Serve per i siti con DataDome (es. Idealista): una sessione già "flaggata"
        resta bloccata, quindi non si ritenta sulla stessa ma se ne crea una pulita.
        Il warm-up (visita a una pagina, di solito la homepage) imposta i cookie
        anti-bot prima di richiedere la pagina di ricerca.
        """
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            session = self._new_session()
            try:
                if warmup:
                    session.get(warmup, timeout=self.timeout)
                    time.sleep(1)
                req_headers = {"Referer": warmup} if warmup else {}
                if headers:
                    req_headers.update(headers)
                resp = session.get(url, timeout=self.timeout, headers=req_headers)
                if resp.status_code == 200 and "geo.captcha" not in resp.text:
                    return resp
                logger.warning("GET(fresh) %s -> HTTP %s (tentativo %s/%s)", url, resp.status_code, attempt, self.retries)
                last_exc = FetchError(f"HTTP {resp.status_code} su {url}")
            except Exception as exc:
                logger.warning("GET(fresh) %s errore: %r (tentativo %s/%s)", url, exc, attempt, self.retries)
                last_exc = exc
            finally:
                session.close()
            if attempt < self.retries:
                time.sleep(self.backoff * attempt)
        raise FetchError(str(last_exc))
