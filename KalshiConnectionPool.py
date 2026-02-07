import asyncio
from KalshiWebSocket import KalshiWebSocket

class KalshiConnectionPool:
    """Manages multiple WebSocket connections with dynamic market additions"""
    
    def __init__(self, orderbook, access_key, private_key_pem, num_connections, max_markets_per_connection):
        self.orderbook = orderbook
        self.access_key = access_key
        self.private_key_pem = private_key_pem
        self.num_connections = num_connections
        self.max_markets_per_connection = max_markets_per_connection
        self.connections = []
        self.tasks = []
        self.next_connection_idx = 0  # Round-robin index
        self.market_to_connection = {}  # Track which connection has which market

    async def initialize(self):
        """Initialize all WebSocket connections"""
        print(f"Initializing {self.num_connections} WebSocket connections...")
        
        for idx in range(self.num_connections):
            ws = KalshiWebSocket(
                orderbook=self.orderbook,
                access_key=self.access_key,
                private_key_pem=self.private_key_pem,
                connection_id=idx + 1
            )
            
            self.connections.append(ws)
            task = asyncio.create_task(ws.run())
            self.tasks.append(task)
            
            await asyncio.sleep(0.05)  # Small delay between connections
        
        # Wait for all connections to be ready
        await asyncio.gather(*[ws.ready.wait() for ws in self.connections])
        print(f"✓ All {len(self.connections)} connections ready")

    async def add_markets(self, tickers):
        """
        Add new markets using round-robin load balancing
        
        Args:
            tickers: List of market tickers to add (can be single ticker or multiple)
        """
        
        for ticker in tickers:
            # Skip if already subscribed
            if ticker in self.market_to_connection:
                print(f"Market {ticker} already subscribed")
                continue
            
            # Find next connection using round-robin
            connection = self.connections[self.next_connection_idx]
            
            # Check if connection is full
            if len(connection.tickers) >= self.max_markets_per_connection:
                # Find a connection with space
                connection = None
                for ws in self.connections:
                    if len(ws.tickers) < self.max_markets_per_connection:
                        connection = ws
                        break
                
                if not connection:
                    print(f"WARNING: All connections full! Cannot add {ticker}")
                    continue
            
            # Add market to connection
            await connection.subscribe([ticker])
            self.market_to_connection[ticker] = connection
            
            # Update round-robin index
            self.next_connection_idx = (self.next_connection_idx + 1) % self.num_connections

    async def remove_markets(self, tickers):
        """
        Remove markets from their respective connections
        
        Args:
            tickers: List of market tickers to remove (can be single ticker or multiple)
        """
        
        for ticker in tickers:
            if ticker not in self.market_to_connection:
                print(f"Market {ticker} not found in any connection")
                continue
            
            connection = self.market_to_connection[ticker]
            await connection.unsubscribe([ticker])
            del self.market_to_connection[ticker]

    async def run_forever(self):
        """Keep all connections running"""
        try:
            await asyncio.gather(*self.tasks)
        except Exception as e:
            print(f"Error in connection pool: {e}")
            raise

    def get_stats(self):
        """Get statistics about connections and markets"""
        total_markets = sum(len(ws.tickers) for ws in self.connections)
        markets_per_conn = [len(ws.tickers) for ws in self.connections]
        
        return {
            "total_connections": len(self.connections),
            "total_markets": total_markets,
            "markets_per_connection": markets_per_conn,
            "average_per_connection": total_markets / len(self.connections) if self.connections else 0,
            "max_markets_per_connection": self.max_markets_per_connection
        }

"""
TESTING:

async def test():
    
    # Load your credentials
    ACCESS_KEY = "***REMOVED-KALSHI-ACCESS-KEY***"
    PRIVATE_KEY_PEM = something
    
    # Create connection pool
    pool = KalshiConnectionPool(
        access_key=ACCESS_KEY,
        private_key_pem=PRIVATE_KEY_PEM,
        num_connections=201,
        max_markets_per_connection=15
    )
    
    # Initialize all connections
    await pool.initialize()
    
    # Simulate dynamic market discovery
    # Your other process would call these methods when it discovers markets
    
    # Add some initial markets
    initial_markets = ["", "KXPRESPERSON-28-GNEWS"]
    await pool.add_markets(initial_markets)
    
    print(f"\nFinal stats: {pool.get_stats()}")

    
    # Simulate discovering new markets over time
    await asyncio.sleep(5)
    await pool.add_markets(["KXSB-26-SEA", "KXSB-26-LAR"])
    print(f"\nFinal stats: {pool.get_stats()}")

    await asyncio.sleep(5)
    await pool.remove_markets(["KXPRESPERSON-28-JVAN"])
    print(f"\nFinal stats: {pool.get_stats()}")

    # Remove a market
    await asyncio.sleep(5)
    await pool.remove_markets(["KXPRESPERSON-28-GNEWS"])
    print(f"\nFinal stats: {pool.get_stats()}")

    # Keep all connections running forever
    await pool.run_forever()


if __name__ == "__main__":
    asyncio.run(test())

"""