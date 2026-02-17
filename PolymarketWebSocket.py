import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

MARKET_CHANNEL = "market"
URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"


class PolymarketWebSocket:
    """Single WebSocket connection handling a subset of markets"""
    
    def __init__(self, orderbook, connection_id):
        self.orderbook = orderbook
        self.connection_id = connection_id
        self.asset_ids = []
        self.ws = None
        self.ready = asyncio.Event()
        self._pinger_task = None
        self._send_lock = asyncio.Lock()
    
    async def _pinger(self):
        try:
            while True:
                await asyncio.sleep(5)
                if not self.ready.is_set() or not self.ws:
                    continue
                try:
                    async with self._send_lock:
                        await self.ws.send("PING")
                except (ConnectionClosed, ConnectionClosedError, OSError):
                    self.ready.clear()
                    return
        except asyncio.CancelledError:
            return

    async def subscribe(self, assets):
        """Add new assets to this connection"""
        await self.ready.wait()
        
        if not assets:
            return
        
        msg = {
            "type": MARKET_CHANNEL,
            "operation": "subscribe",
            "assets_ids": assets
        }
        try:
            async with self._send_lock:
                await self.ws.send(json.dumps(msg))
        except (ConnectionClosed, ConnectionClosedError, OSError):
            self.ready.clear()
            return
            
        self.asset_ids.extend(assets)
        print(f"[Connection {self.connection_id}] Added {len(assets)} assets (total: {len(self.asset_ids)})")
    
    async def unsubscribe(self, assets):
        """Remove assets from this connection"""
        await self.ready.wait()
        
        if not assets:
            return
        
        msg = {
            "type": MARKET_CHANNEL,
            "operation": "unsubscribe",
            "assets_ids": assets
        }
        try:
            async with self._send_lock:
                await self.ws.send(json.dumps(msg))
        except (ConnectionClosed, ConnectionClosedError, OSError):
            self.ready.clear()
            return
        
        self.asset_ids = [a for a in self.asset_ids if a not in assets]
        print(f"[Connection {self.connection_id}] Removed {len(assets)} assets (total: {len(self.asset_ids)})")

    async def handle_message(self, message):
        if message == "PONG":
            return
        if message == "PING":
            try:
                async with self._send_lock:
                    if self.ws:
                        await self.ws.send("PONG")
            except (ConnectionClosed, ConnectionClosedError, OSError):
                self.ready.clear()
            return

        self.orderbook.update_poly_orderbook(message)

    
    async def _resubscribe_existing(self):
        if not self.asset_ids:
            return
        msg = {"type": MARKET_CHANNEL, "operation": "subscribe", "assets_ids": self.asset_ids}
        try:
            async with self._send_lock:
                await self.ws.send(json.dumps(msg))
        except (ConnectionClosed, ConnectionClosedError, OSError):
            self.ready.clear()
            return

    async def run(self):
        backoff = 1
        while True:
            try:
                self.ready.clear()
                async with websockets.connect(
                    URL,
                    ping_interval=None,  # Polymarket uses app-level PING/PONG
                ) as ws:
                    self.ws = ws
                    self.ready.set()
                    backoff = 1
                    print(f"[Connection {self.connection_id}] Connected and ready")

                    # start heartbeat
                    if self._pinger_task:
                        self._pinger_task.cancel()
                    self._pinger_task = asyncio.create_task(self._pinger())

                    # resubscribe what we already track
                    await self._resubscribe_existing()

                    async for message in ws:
                        await self.handle_message(message)

            except (ConnectionClosed, ConnectionClosedError, OSError) as e:
                print(f"[Connection {self.connection_id}] WS dropped ({e}); reconnecting in {backoff}s")
            finally:
                self.ready.clear()
                if self._pinger_task:
                    self._pinger_task.cancel()
                    self._pinger_task = None
                self.ws = None
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)