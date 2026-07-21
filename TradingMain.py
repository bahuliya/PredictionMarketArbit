import asyncio
import logging
import os
import uvicorn
from Orderbook import Orderbook
from KalshiConnectionPool import KalshiConnectionPool
from PolymarketConnectionPool import PolymarketConnectionPool
from RedisListner import RedisListener
from event_hub import EventHub
from gui_backend import build_gui_app
from execution import ExecutionManager, KalshiOrderExecutor, PolymarketOrderExecutor

def setup_logging(level=logging.INFO, log_path="logs/orderbook.log"):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)

    root.handlers[:] = [file_handler]

# Load your Kalshi credentials
ACCESS_KEY = "***REMOVED-KALSHI-ACCESS-KEY***"
PRIVATE_KEY_PEM = b"""-----BEGIN RSA PRIVATE KEY-----
***REMOVED-KALSHI-PRIVATE-KEY***==
-----END RSA PRIVATE KEY-----"""


async def main():
    # 1. Initialize orderbook
    hub = EventHub()

    # Execution layer: OFF by default. Setting ENABLE_LIVE_TRADING=1 in keys.env
    # is NOT enough on its own to place real orders - KalshiOrderExecutor and
    # PolymarketOrderExecutor.place_order() are unimplemented stubs (see
    # execution/) until real order-placement logic is built and reviewed.
    live_trading_enabled = os.getenv("ENABLE_LIVE_TRADING", "0") == "1"
    execution_manager = ExecutionManager(
        kalshi_executor=KalshiOrderExecutor(ACCESS_KEY, PRIVATE_KEY_PEM),
        poly_executor=PolymarketOrderExecutor(),
        live_trading_enabled=live_trading_enabled,
    )

    orderbook = Orderbook(hub=hub, executor=execution_manager)

    # Start GUI backend (serves WS at /ws and optionally the built frontend)
    app = build_gui_app(orderbook, hub)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning", access_log=False, log_config=None)
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())

    # 2. Create Kalshi pool (only orderbook_delta)
    kalshi_pool = KalshiConnectionPool(
        orderbook=orderbook,
        access_key=ACCESS_KEY,
        private_key_pem=PRIVATE_KEY_PEM,
        num_connections=20,
        max_markets_per_connection=50
    )
    
    # 3. Create Polymarket pool
    poly_pool = PolymarketConnectionPool(
        orderbook=orderbook,
        num_connections=20,
        max_assets_per_connection=50
    )
    
    # 4. Initialize both pools
    await kalshi_pool.initialize()
    await poly_pool.initialize()
    
    # 5. Start Redis listener
    redis_listener = RedisListener(
        orderbook=orderbook,
        kalshi_ws=kalshi_pool,
        poly_ws=poly_pool
    )

    asyncio.create_task(redis_listener.start())
    # 6. Run forever

    await asyncio.Future()


if __name__ == "__main__":
    setup_logging(logging.INFO, "logs/orderbook.log")
    asyncio.run(main())