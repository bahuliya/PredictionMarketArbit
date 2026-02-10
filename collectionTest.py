from ArbitrageMatcher import ArbitrageMatcher
from EmbeddingConversion import EmbeddingConversion
from collectors.kalshi_collector import AsyncKalshiCollector
from collectors.polymarket_collector import AsyncPolymarketCollector
from MatchPublisher import MatchPublisher
import asyncio
from datetime import datetime, timezone
import time

'''
Current Model - Qwen/Qwen3-Embedding-4B
Test Model - "all-MiniLM-L6-v2"
'''

BATCH_SIZE = 8
SAVE_INTERVAL = 60
UPDATE_INTERVAL = 30

async def main():

    # Initialize Objects

    embedder = EmbeddingConversion(
        model_name="Qwen/Qwen3-Embedding-4B",
        batch_size=BATCH_SIZE,
        save_interval=SAVE_INTERVAL
    )

    # Create collectors
    kalshi = AsyncKalshiCollector()
    poly = AsyncPolymarketCollector()
    
    # Start collectors
    poly.last_update_close = datetime.now(timezone.utc)

    kalshi_markets, poly_markets = await asyncio.gather(
        kalshi.fetch_markets(),
        poly.fetch_markets()
    )

    print("Starting embedding for Kalshi and Polymarket")
    embedder.add_markets(kalshi_markets + poly_markets)
    


if __name__ == "__main__":
    asyncio.run(main())