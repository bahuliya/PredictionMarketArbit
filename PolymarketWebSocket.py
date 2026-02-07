import asyncio
import json
import websockets

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
        await self.ws.send(json.dumps(msg))
        
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
        await self.ws.send(json.dumps(msg))
        
        self.asset_ids = [a for a in self.asset_ids if a not in assets]
        print(f"[Connection {self.connection_id}] Removed {len(assets)} assets (total: {len(self.asset_ids)})")

    async def handle_message(self, message):
        """
        Process incoming market data
        Override this method with your business logic
        """
        if message == "PONG":
            return
        
        self.orderbook.update_poly_orderbook(message)
        # print(f"[Connection {self.connection_id}] Received: {message[:100]}...")

    async def run(self):
        """Connect to WebSocket and process messages"""
        # Note: ping/pong is handled automatically by websockets library
        # Set ping_interval and ping_timeout if you want custom values
        async with websockets.connect(URL) as ws:
            self.ws = ws
            self.ready.set()
            
            print(f"[Connection {self.connection_id}] Connected and ready")
            
            # Process messages
            async for message in ws:
                await self.handle_message(message)
    