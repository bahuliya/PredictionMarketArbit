# redis_listener.py
import asyncio
import json
from redis import asyncio as aioredis

class RedisListener:
    def __init__(self, orderbook, kalshi_ws, poly_ws):
        self.orderbook = orderbook
        self.kalshi_ws = kalshi_ws
        self.poly_ws = poly_ws   
 
    async def start(self):
        """Start listening for new matches from discovery process"""
        redis = await aioredis.from_url("redis://localhost")
        pubsub = redis.pubsub()
        
        # Subscribe to new_matches channel
        await pubsub.subscribe("new_matches")
        
        print("Listening for matches from discovery process...")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                await self._handle_new_match(message["data"])
    
    async def _handle_new_match(self, data):
        """Handle incoming match from Redis"""
        try:
            match = json.loads(data)
            
            # Add to orderbook
            markets = self.orderbook.add_match(match)
            
            if markets:
                # Subscribe WebSockets to new markets
                await self.kalshi_ws.add_markets(markets["kalshi"])
                await self.poly_ws.add_assets(markets["poly"])
                
                print(f"✓ Subscribed to new match: {match['kalshi_ticker']}")
        
        except Exception as e:
            print(f"✗ Error handling new match: {e}")