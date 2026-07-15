from __future__ import annotations

import logging
import time

import requests

from .models import Listing

logger = logging.getLogger("subitobot.notifier")


def format_listing(listing: Listing) -> str:
    """Testo del messaggio Telegram per un annuncio."""
    e = listing.extra
    if listing.category == "auto":
        parts = [f"🚗 {listing.title}"]
        line = []
        if listing.price is not None:
            line.append(f"{listing.price:,.0f} €".replace(",", "."))
        if e.get("km") is not None:
            line.append(f"{e['km']:,} km".replace(",", "."))
        if e.get("anno"):
            line.append(str(e["anno"]))
        if e.get("carburante"):
            line.append(e["carburante"])
        if line:
            parts.append(" · ".join(line))
        if e.get("convenienza") is not None:
            parts.append(f"📈 convenienza {e['convenienza']:,.0f}".replace(",", "."))
    else:  # affitti
        parts = [f"🏠 {listing.title}"]
        line = []
        if listing.price is not None:
            line.append(f"{listing.price:,.0f} €/mese".replace(",", "."))
        if e.get("mq"):
            line.append(f"{e['mq']} mq")
        if e.get("locali"):
            line.append(f"{e['locali']} locali")
        if line:
            parts.append(" · ".join(line))
    if listing.city:
        parts.append(f"📍 {listing.city}")
    parts.append(listing.url)
    return "\n".join(parts)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, retries: int = 3):
        self.token = token
        self.chat_id = chat_id
        self.retries = retries
        self.api = f"https://api.telegram.org/bot{token}/sendMessage"

    def send(self, text: str) -> bool:
        """Invia un messaggio. I parametri passano come form-data: niente problemi
        di encoding con spazi, €, a capo (bug della vecchia URL GET)."""
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }
        for attempt in range(1, self.retries + 1):
            try:
                resp = requests.post(self.api, data=payload, timeout=15)
                if resp.status_code == 200 and resp.json().get("ok"):
                    return True
                logger.warning("Telegram HTTP %s: %s", resp.status_code, resp.text[:200])
            except Exception as exc:
                logger.warning("Errore invio Telegram: %r (tentativo %s/%s)", exc, attempt, self.retries)
            time.sleep(1.5 * attempt)
        return False

    def notify(self, listing: Listing) -> bool:
        return self.send(format_listing(listing))
