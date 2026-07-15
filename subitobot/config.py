from __future__ import annotations

import json


class ConfigError(Exception):
    pass


def load_config(path: str = "config.json") -> dict:
    """Carica e valida config.json, con messaggi d'errore chiari."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"Config non trovata: {path}. Copia config.example.json in {path}.")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config.json non è JSON valido: {exc}")

    tg = cfg.get("telegram") or {}
    if not tg.get("token") or not tg.get("chat_id"):
        raise ConfigError("Manca 'telegram.token' o 'telegram.chat_id' in config.json.")

    searches = cfg.get("searches")
    if not isinstance(searches, list) or not searches:
        raise ConfigError("'searches' deve essere una lista non vuota.")

    names = set()
    for i, s in enumerate(searches):
        for req in ("name", "provider", "category", "url"):
            if not s.get(req):
                raise ConfigError(f"searches[{i}]: manca il campo obbligatorio '{req}'.")
        if s["category"] not in ("auto", "affitti"):
            raise ConfigError(f"searches[{i}] ('{s['name']}'): category deve essere 'auto' o 'affitti'.")
        if s["name"] in names:
            raise ConfigError(f"Nome ricerca duplicato: '{s['name']}' (devono essere unici).")
        names.add(s["name"])

    cfg.setdefault("poll_seconds", 300)
    return cfg
