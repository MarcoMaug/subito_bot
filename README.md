# Subito bot

Bot headless che controlla periodicamente le ricerche su **subito.it** (auto e
affitti) e invia su **Telegram** solo i **nuovi annunci**.

## Perché questa versione

I siti di annunci (Subito, Immobiliare, Idealista) usano protezioni anti-bot
(Akamai/DataDome): `requests`/`curl` normali vengono bloccati con `403 Access
Denied`. Il bot supera il blocco impersonando il TLS di Chrome tramite
[`curl_cffi`](https://github.com/lexiforest/curl_cffi), e legge gli annunci dal
JSON già incorporato nelle pagine di subito.it (`__NEXT_DATA__`), senza dover
mappare a mano i parametri delle API interne.

## Setup

```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
cp config.example.json config.json   # poi inserisci token e ricerche
```

### config.json

- `telegram.token` / `telegram.chat_id`: bot Telegram e chat destinataria.
- `poll_seconds`: intervallo tra i controlli (default 300 = 5 min).
- `searches`: lista di ricerche. Per ognuna:
  - `name`: identificativo univoco (usato per il dedup).
  - `provider`: `subito` (unico attivo; immobiliare/idealista in backlog).
  - `category`: `auto` oppure `affitti`.
  - `url`: **l'URL normale di ricerca su subito.it**, con tutti i filtri già
    impostati (basta copiarlo dal browser).
  - `filters` (opzionale): filtri prima della notifica, es. `convenienza_min`
    (auto) o `price_max`.

## Uso

```bash
./venv/bin/python main.py            # loop continuo (ogni poll_seconds)
./venv/bin/python main.py --once     # un solo ciclo (per test)
```

Al **primo giro** ogni ricerca fa un *seed* silenzioso: registra gli annunci
esistenti **senza notificarli**. Dai giri successivi arrivano solo i nuovi.
Lo stato è in `seen.db` (SQLite), il dedup è per id stabile dell'annuncio.

## Esecuzione su server

Il loop interno riusa la sessione (e i cookie anti-bot) tra i cicli, quindi è
preferibile lasciarlo girare come processo unico invece di lanciarlo da cron:

```bash
nohup ./venv/bin/python main.py >/dev/null 2>&1 &
```

Oppure con un servizio `systemd` che esegue `main.py` e si riavvia da solo.

## Backlog

- Provider `immobiliare` (API `api-next`, JSON pulito) e `idealista` (HTML),
  con lo stesso `Fetcher` e la stessa interfaccia `Provider`.
- Fallback Playwright per eventuali siti che dovessero resistere a `curl_cffi`.
