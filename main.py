from __future__ import annotations

import argparse
import logging
from logging.handlers import RotatingFileHandler

from subitobot.config import ConfigError, load_config
from subitobot.fetcher import Fetcher
from subitobot.notifier import TelegramNotifier
from subitobot.runner import run_loop, run_once
from subitobot.store import Store


def setup_logging() -> None:
    handler = RotatingFileHandler("subitobot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[handler, console])


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot notifiche nuovi annunci Subito (auto e affitti).")
    parser.add_argument("--config", default="config.json", help="Percorso config (default: config.json)")
    parser.add_argument("--once", action="store_true", help="Esegui un solo ciclo ed esci (per test).")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("subitobot.main")

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        log.error("Config non valida: %s", exc)
        raise SystemExit(1)

    fetcher = Fetcher()
    store = Store()
    notifier = TelegramNotifier(cfg["telegram"]["token"], str(cfg["telegram"]["chat_id"]))

    try:
        if args.once:
            run_once(cfg, fetcher, store, notifier)
        else:
            run_loop(cfg, fetcher, store, notifier)
    except KeyboardInterrupt:
        log.info("Interrotto dall'utente.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
