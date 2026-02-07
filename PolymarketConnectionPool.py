import asyncio
from PolymarketWebSocket import PolymarketWebSocket

class PolymarketConnectionPool:
    """Manages multiple WebSocket connections with dynamic asset additions"""
    
    def __init__(self, orderbook, num_connections=20, max_assets_per_connection=50):
        self.orderbook = orderbook
        self.num_connections = num_connections
        self.max_assets_per_connection = max_assets_per_connection
        self.connections = []
        self.tasks = []
        self.next_connection_idx = 0  # Round-robin index
        self.asset_to_connection = {}  # Track which connection has which asset

    async def initialize(self):
        """Initialize all WebSocket connections"""
        print(f"Initializing {self.num_connections} WebSocket connections...")
        
        for idx in range(self.num_connections):
            ws = PolymarketWebSocket(orderbook=self.orderbook, connection_id=idx + 1)
            
            self.connections.append(ws)
            task = asyncio.create_task(ws.run())
            self.tasks.append(task)
            
            await asyncio.sleep(0.05)  # Small delay between connections
        
        # Wait for all connections to be ready
        await asyncio.gather(*[ws.ready.wait() for ws in self.connections])
        print(f"✓ All {len(self.connections)} connections ready")

    async def add_assets(self, asset_ids):
        """
        Add new assets using round-robin load balancing
        
        Args:
            asset_ids: List of asset IDs to add (can be single ID or multiple)
        """
        
        for asset_id in asset_ids:
            # Skip if already subscribed
            if asset_id in self.asset_to_connection:
                print(f"Asset {asset_id} already subscribed")
                continue
            
            # Find next connection using round-robin
            connection = self.connections[self.next_connection_idx]
            
            # Check if connection is full
            if len(connection.asset_ids) >= self.max_assets_per_connection:
                # Find a connection with space
                connection = None
                for ws in self.connections:
                    if len(ws.asset_ids) < self.max_assets_per_connection:
                        connection = ws
                        break
                
                if not connection:
                    print(f"WARNING: All connections full! Cannot add {asset_id}")
                    continue
            
            # Add asset to connection
            await connection.subscribe([asset_id])
            self.asset_to_connection[asset_id] = connection
            
            # Update round-robin index
            self.next_connection_idx = (self.next_connection_idx + 1) % self.num_connections

    async def remove_assets(self, asset_ids):
        """
        Remove assets from their respective connections
        
        Args:
            asset_ids: List of asset IDs to remove (can be single ID or multiple)
        """
        
        for asset_id in asset_ids:
            if asset_id not in self.asset_to_connection:
                print(f"Asset {asset_id} not found in any connection")
                continue
            
            connection = self.asset_to_connection[asset_id]
            await connection.unsubscribe([asset_id])
            del self.asset_to_connection[asset_id]

    def get_stats(self):
        """Get statistics about connections and assets"""
        total_assets = sum(len(ws.asset_ids) for ws in self.connections)
        assets_per_conn = [len(ws.asset_ids) for ws in self.connections]
        
        return {
            "total_connections": len(self.connections),
            "total_assets": total_assets,
            "assets_per_connection": assets_per_conn,
            "max_assets_per_connection": self.max_assets_per_connection
        }

    async def run_forever(self):
        """Keep all connections running"""
        try:
            await asyncio.gather(*self.tasks)
        except Exception as e:
            print(f"Error in connection pool: {e}")
            raise

"""
TESTING:

async def test():
    
    # Create connection pool (20 connections, max 50 assets each)
    pool = PolymarketConnectionPool(
        num_connections=20,
        max_assets_per_connection=50
    )
    
    # Initialize all connections
    await pool.initialize()
    
    # Add some initial assets
    initial_assets = [
        "91737931954079461205792748723730956466398437395923414328893692961489566016241",
        "47021554520147489198499363137978179318351470490672224768430579421357197997727"
    ]
    await pool.add_assets(initial_assets)
    
    # Show stats
    print(f"\nStats after initial assets: {pool.get_stats()}")
    
    # Simulate discovering new assets over time
    await asyncio.sleep(5)
    new_assets = [
        "67458767289404585234744660199191729864647269546936372565997492523516079162996",
        "113554675031456886662456333518442351760965732494459471513820718399879139049322"
    ]
    await pool.add_assets(new_assets)
    
    # Remove an asset
    await asyncio.sleep(5)
    await pool.remove_assets([initial_assets[0]])
    
    print(f"\nFinal stats: {pool.get_stats()}")
    
    # Keep all connections running forever
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(test())

"""