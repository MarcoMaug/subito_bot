from __future__ import annotations

from abc import ABC, abstractmethod

from ..fetcher import Fetcher
from ..models import Listing


class Provider(ABC):
    """Interfaccia comune. Un provider scarica gli annunci di una ricerca
    e li restituisce normalizzati come lista di Listing."""

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher

    @abstractmethod
    def fetch(self, search: dict) -> list[Listing]:
        """`search` è un elemento della config (name, category, url, ...)."""
        raise NotImplementedError
