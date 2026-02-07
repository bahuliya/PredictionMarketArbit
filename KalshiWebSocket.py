import asyncio
import base64
import time
import json
import websockets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
#from Orderbook import Orderbook

URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"


class KalshiWebSocket:
    """Single WebSocket connection handling a subset of markets"""
    
    def __init__(self, orderbook, access_key, private_key_pem, connection_id):
        self.orderbook = orderbook
        self.access_key = access_key
        self.private_key_pem = private_key_pem
        self.connection_id = connection_id
        self.ws_path = "/trade-api/ws/v2"
        self.tickers = []
        self.sid = None
        self.ws = None
        self.ready = asyncio.Event()

    def generate_auth_headers(self):
        """Generate authentication headers for Kalshi API"""
        timestamp = str(int(time.time() * 1000))
        message = (timestamp + "GET" + self.ws_path).encode()
        
        private_key = serialization.load_pem_private_key(
            self.private_key_pem,
            password=None,
        )
        
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )

        return {
            "KALSHI-ACCESS-KEY": self.access_key,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

    async def subscribe(self, tickers):
        """Add new tickers to this connection"""
        await self.ready.wait()  # Wait until connection is established
        
        if not tickers:
            return
        
        # If this is initial subscription (no sid yet), use subscribe command
        if not self.sid:
            await self.ws.send(json.dumps({
                "id": 1,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_tickers": tickers
                }
            }))
        else:
            # Update existing subscription
            await self.ws.send(json.dumps({
                "id": 2,
                "cmd": "update_subscription",
                "params": {
                    "sid": self.sid,
                    "market_tickers": tickers,
                    "action": "add_markets"
                }
            }))
        
        self.tickers.extend(tickers)
        print(f"[Connection {self.connection_id}] Added {len(tickers)} markets (total: {len(self.tickers)})")

    async def unsubscribe(self, tickers):
        """Remove tickers from this connection"""
        await self.ready.wait()
        
        if not tickers or not self.sid:
            return
        
        await self.ws.send(json.dumps({
            "id": 3,
            "cmd": "update_subscription",
            "params": {
                "sid": self.sid,
                "market_tickers": tickers,
                "action": "delete_markets"
            }
        }))
        
        self.tickers = [t for t in self.tickers if t not in tickers]
        print(f"[Connection {self.connection_id}] Removed {len(tickers)} markets (total: {len(self.tickers)})")
        

    async def run(self):
        """Connect to WebSocket and process messages"""
        headers = self.generate_auth_headers()
        
        async with websockets.connect(URL, additional_headers=headers) as ws:
            self.ws = ws
            self.ready.set()  # Signal that connection is ready
            
            print(f"[Connection {self.connection_id}] Connected and ready")
            
            # Process messages
            async for msg in ws:
                data = json.loads(msg)
                
                # Handle subscription confirmation
                if data.get("type") == "subscribed":
                    self.sid = data["msg"]["sid"]
                    # print(f"[Connection {self.connection_id}] Subscribed successfully")
                    continue
                
                self.orderbook.update_kalshi_orderbook(data)


