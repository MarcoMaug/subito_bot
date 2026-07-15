from __future__ import annotations

from ..fetcher import Fetcher
from .base import Provider
from .subito import SubitoProvider

# Registry dei provider disponibili. Immobiliare e Idealista sono nel backlog:
# useranno lo stesso Fetcher (curl_cffi) e la stessa interfaccia Provider.
_REGISTRY: dict[str, type[Provider]] = {
    "subito": SubitoProvider,
}


def get_provider(name: str, fetcher: Fetcher) -> Provider:
    try:
        cls = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"Provider '{name}' non disponibile. Disponibili: {sorted(_REGISTRY)}"
        )
    return cls(fetcher)
