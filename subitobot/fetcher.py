from __future__ import annotations

import json
import logging
import random
import re
import string
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

    @staticmethod
    def _proxies(proxy: str | None):
        """Da una stringa 'http://user:pass@host:port' costruisce il dict per curl_cffi."""
        return {"http": proxy, "https": proxy} if proxy else None

    @staticmethod
    def _rotate_proxy_session(proxy: str) -> str:
        """Sostituisce il 'session-XXXX' nella password del proxy (sintassi iproyal)
        con un id casuale: senza questo, ogni retry su get_fresh riusa la stessa IP
        sticky, quindi se quell'IP e' gia' bloccata (es. Akamai su immobiliare.it)
        tutti i tentativi falliscono identici invece di provare IP diverse."""
        new_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        return re.sub(r"session-[A-Za-z0-9]+", f"session-{new_id}", proxy)

    def get(self, url: str, proxy: str | None = None, **kwargs):
        """GET con retry esponenziale. Rilancia FetchError se esaurisce i tentativi."""
        proxies = self._proxies(proxy)
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout, proxies=proxies, **kwargs)
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

    def get_next_data(self, url: str, warmup: str | None = None, proxy: str | None = None) -> dict:
        """Scarica una pagina e restituisce il JSON incorporato in __NEXT_DATA__.

        Con `warmup` usa una sessione nuova che visita prima quella pagina
        (imposta i cookie anti-bot): serve per gli endpoint come
        immobiliare `/search-list/` che, colpiti "a freddo", danno 403."""
        resp = self.get_fresh(url, warmup=warmup, proxy=proxy) if warmup else self.get(url, proxy=proxy)
        match = _NEXT_DATA_RE.search(resp.text)
        if not match:
            raise FetchError(f"__NEXT_DATA__ non trovato in {url}")
        return json.loads(match.group(1))

    def get_json(self, url: str, **kwargs) -> dict:
        resp = self.get(url, **kwargs)
        return resp.json()

    def get_fresh(self, url: str, warmup: str | None = None, headers: dict | None = None, proxy: str | None = None):
        """GET usando una sessione NUOVA a ogni tentativo, con eventuale warm-up.

        Serve per i siti con DataDome (es. Idealista): una sessione già "flaggata"
        resta bloccata, quindi non si ritenta sulla stessa ma se ne crea una pulita.
        Il warm-up (visita a una pagina, di solito la homepage) imposta i cookie
        anti-bot prima di richiedere la pagina di ricerca.
        """
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            session = self._new_session()
            attempt_proxy = self._rotate_proxy_session(proxy) if proxy else None
            proxies = self._proxies(attempt_proxy)
            try:
                if warmup:
                    session.get(warmup, timeout=self.timeout, proxies=proxies)
                    time.sleep(1)
                req_headers = {"Referer": warmup} if warmup else {}
                if headers:
                    req_headers.update(headers)
                resp = session.get(url, timeout=self.timeout, headers=req_headers, proxies=proxies)
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
