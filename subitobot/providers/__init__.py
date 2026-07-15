from __future__ import annotations

from ..fetcher import Fetcher
from .base import Provider
from .idealista import IdealistaProvider
from .immobiliare import ImmobiliareProvider
from .subito import SubitoProvider

_REGISTRY: dict[str, type[Provider]] = {
    "subito": SubitoProvider,
    "immobiliare": ImmobiliareProvider,
    "idealista": IdealistaProvider,
}


def get_provider(name: str, fetcher: Fetcher) -> Provider:
    try:
        cls = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"Provider '{name}' non disponibile. Disponibili: {sorted(_REGISTRY)}"
        )
    return cls(fetcher)
