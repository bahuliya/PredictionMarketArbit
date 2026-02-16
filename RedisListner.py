# redis_listener.py
import asyncio
import json
from redis import asyncio as aioredis

class RedisListener:
    def __init__(self, orderbook, kalshi_ws, poly_ws):
        self.orderbook = orderbook
        self.kalshi_ws = kalshi_ws
        self.poly_ws = poly_ws
        self.redis_url = "redis://localhost:6379"

    async def start(self):
        """Start listening for new matches from discovery process."""
        while True:
            try:
                redis = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    retry_on_timeout=True,
                )
                pubsub = redis.pubsub(ignore_subscribe_messages=True)
                await pubsub.subscribe("new_matches")
                print("Listening for matches from discovery process...")

                while True:
                    message = await pubsub.get_message(timeout=1.0)
                    if message is None:
                        # heartbeat to detect dead connections
                        await redis.ping()
                        continue
                    await self._handle_new_match(message["data"])

            except Exception as e:
                print(f"Redis listener error, retrying in 1s: {e}")
                await asyncio.sleep(1)

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
