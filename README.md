# Orderbook — Kalshi ↔ Polymarket Arbitrage Detector

Detects arbitrage opportunities between equivalent [Kalshi](https://kalshi.com) and
[Polymarket](https://polymarket.com) prediction markets by matching markets to each
other, streaming live order books for both, and flagging spreads that clear a target
ROI. Ships with a FastAPI/WebSocket backend and a small React GUI for watching matches
and arb hits in real time.

**Trade execution is scaffolded but disabled by default.** Out of the box this is a
detection/alerting tool — see [Execution layer](#execution-layer-disabled-by-default)
before doing anything else.

## Architecture

The system is two independent, long-running processes that only talk to each other
through Redis pub/sub:

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│   Discovery / Matching      │        │   Trading / Orderbook        │
│   (CollectionMain.py)       │        │   (TradingMain.py)           │
│                              │        │                               │
│  Kalshi + Polymarket REST ──┼──┐     │  Kalshi + Polymarket WS  ────┼──> live order books
│  Sentence-Transformer        │  │     │  Orderbook.py             ──┼──> arbitrage.py (ROI calc)
│  embeddings (candidates) ────┼──┤     │  RedisListner.py  <──────────┼── subscribes "new_matches" /
│  Gemini (Vertex AI) confirms │  │     │                               │   "removed_matches"
│  "same underlying event" ────┼──┴──>  Redis pub/sub  ──────────────┼──┘
│  MatchPublisher.py           │        │  EventHub -> gui_backend.py  │
└─────────────────────────────┘        │  (FastAPI + WebSocket) ──────┼──> web/ (React GUI)
                                        └──────────────────────────────┘
```

- **Discovery/matching** (`CollectionMain.py`): fetches markets from both platforms
  (`collectors/`), embeds their descriptions (`EmbeddingConversion.py`), narrows to
  top-N nearest candidates, then asks Gemini (via Vertex AI) to confirm whether two
  markets represent the exact same underlying event (`ArbitrageMatcher.py`). Confirmed
  matches are published to Redis (`MatchPublisher.py`).
- **Trading/orderbook** (`TradingMain.py`): subscribes to Redis for new/removed matches
  (`RedisListner.py`), opens WebSocket connections to Kalshi and Polymarket for every
  matched market (`KalshiConnectionPool.py` / `PolymarketConnectionPool.py`,
  `KalshiWebSocket.py` / `PolymarketWebSocket.py`), maintains live order books
  (`Orderbook.py`), and evaluates arbitrage ROI on every book update
  (`arbitrage.py`). Events (`arb_hit`, book updates, etc.) are broadcast over
  WebSocket to the GUI via `event_hub.py` and `gui_backend.py`.

The two processes are decoupled on purpose: discovery/matching is slow and
LLM-dependent, while trading/orderbook needs to react to book updates with low
latency. Redis is the only coupling between them.

## Prerequisites

- Python 3.11+
- Node.js 18+ (for the GUI, optional)
- A running Redis server (`redis://localhost:6379` by default) reachable by both
  processes
- A Google Cloud project with Vertex AI enabled and billing turned on (for Gemini
  market matching), plus local `gcloud` application-default credentials
- Kalshi API credentials (access key + RSA private key) if you want the trading
  process to actually connect to Kalshi

## Setup

```bash
# 1. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Frontend (optional, only needed to view the GUI)
cd web && npm install && cd ..

# 3. Google Cloud auth for Gemini matching (Vertex AI)
gcloud auth application-default login
gcloud config set project <your-gcp-project-id>

# 4. Redis (must be running locally, or point RedisListner/MatchPublisher at
#    your own instance)
redis-server
```

### Credentials (`keys.env`)

Copy the template below into a `keys.env` file at the repo root (this file is
git-ignored and must never be committed):

```dotenv
# Kalshi trading credentials (used by TradingMain.py)
# KALSHI_PRIVATE_KEY_PEM must have its newlines escaped as \n on a single line.
KALSHI_ACCESS_KEY=<your-kalshi-access-key>
KALSHI_PRIVATE_KEY_PEM="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# Off by default. See "Execution layer" below - even with this set to 1,
# no real orders can be placed until the executor stubs are implemented.
ENABLE_LIVE_TRADING=0
```

Gemini matching authenticates via Vertex AI using your local `gcloud`
application-default credentials (see Setup step 3), not an API key.

> If you ever accidentally commit a real credential, treat it as compromised:
> rotate it immediately, then scrub it from git history (e.g. with
> [`git-filter-repo`](https://github.com/newren/git-filter-repo)) before it's
> pushed anywhere further.

## Running

Run the two processes independently (each in its own terminal), with Redis already
running:

```bash
# Discovery / matching - fetches markets, embeds, matches via Gemini, publishes to Redis
python CollectionMain.py

# Trading / orderbook - consumes matches, maintains live books, detects arbitrage, serves GUI
python TradingMain.py
```

`TradingMain.py` serves the GUI backend on `http://localhost:8000` (WebSocket at
`/ws`). To develop the frontend with hot reload:

```bash
cd web
npm run dev
```

To build the frontend so `TradingMain.py` can serve it directly from `web/dist`:

```bash
cd web
npm run build
```

## Execution layer (disabled by default)

`execution/` scaffolds an automated trade-execution layer that `Orderbook.py` notifies
on every `arb_hit`:

- `ExecutionManager` (`execution/manager.py`) always logs opportunities, but only
  schedules order placement when `ENABLE_LIVE_TRADING=1` in `keys.env`.
- `KalshiOrderExecutor` and `PolymarketOrderExecutor` (`execution/kalshi_executor.py`,
  `execution/polymarket_executor.py`) are stubs whose `place_order()` raises
  `NotImplementedError` — so **even with live trading "enabled", no real orders can
  be placed** until real order-placement logic is implemented and reviewed there.

This is intentional: today the project is a detection/alerting tool. Turning it into
a real trading bot requires implementing those executors and thoroughly testing them
(ideally against a paper/sandbox environment first).

## Repository layout

```
CollectionMain.py            Discovery/matching process entry point
TradingMain.py                Trading/orderbook process entry point
ArbitrageMatcher.py           Gemini-based market matching
EmbeddingConversion.py        Sentence-transformer embeddings for market text
arbitrage.py                  ROI / arbitrage sizing calculation
Orderbook.py                  Combined Kalshi + Polymarket order book state
event_hub.py                  In-process event bus -> GUI
gui_backend.py                FastAPI app serving the WebSocket API + built GUI
MatchPublisher.py             Publishes matches/removals to Redis
RedisListner.py                Subscribes to matches/removals from Redis
KalshiConnectionPool.py       Pool of Kalshi WebSocket connections
KalshiWebSocket.py             Single Kalshi WebSocket client
PolymarketConnectionPool.py   Pool of Polymarket WebSocket connections
PolymarketWebSocket.py         Single Polymarket WebSocket client
collectors/                   REST collectors for Kalshi/Polymarket market snapshots
execution/                     Disabled-by-default trade execution layer (see above)
redis_pusher/                  Manual scripts for pushing test matches to Redis
web/                            React + Vite GUI
```

## Notes on data files

`data/*.pkl`, `data/*.json`, `failures/*.json`, and `logs/*.log` are runtime-generated
artifacts (embeddings cache, category cache, matching/mapping failure logs, process
logs) and are git-ignored — they're regenerated automatically when you run the
processes.
