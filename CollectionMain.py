from ArbitrageMatcher import ArbitrageMatcher
from EmbeddingConversion import EmbeddingConversion
from collectors.kalshi_collector import AsyncKalshiCollector
from collectors.polymarket_collector import AsyncPolymarketCollector
from MatchPublisher import MatchPublisher
import asyncio, time, os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv("keys.env")
'''
Current Model - Qwen/Qwen3-Embedding-4B
Test Model - "all-MiniLM-L6-v2"

Gemini auth is via Vertex AI (see ArbitrageMatcher) using local gcloud
application-default credentials, not GEMINI_API_KEY.
'''
TOP_N = 10
BATCH_SIZE = 32
SAVE_INTERVAL = 60
UPDATE_INTERVAL = 30
GEMINI_BATCH_SIZE = 32

async def main():

    # Initialize Objects

    embedder = EmbeddingConversion(
        model_name="all-MiniLM-L6-v2",
        batch_size=32,
        save_interval=SAVE_INTERVAL
    )
    
    publisher = MatchPublisher()

    # Create collectors
    kalshi = AsyncKalshiCollector()
    poly = AsyncPolymarketCollector()

    matcher = ArbitrageMatcher(top_n=TOP_N, gemini_batch_size=GEMINI_BATCH_SIZE, max_concurrent=GEMINI_BATCH_SIZE)
    
    # Start collectors
    poly.last_update_close = datetime.now(timezone.utc)

    kalshi_markets, poly_markets = await asyncio.gather(
        kalshi.fetch_markets(),
        poly.fetch_markets()
    )

    kalshi.last_update = time.time()
    print(kalshi.last_update)


    print("Starting embedding for Kalshi")
    embedder.add_markets(kalshi_markets)
    
    print("Starting embedding for Polymarket")
    embedder.add_markets(poly_markets)


    async for match in matcher.run_initial_matching(
        embedder.all_markets,
        embedder.all_embeddings
    ):
        await publisher.publish_new_match(match)
    
    
    # Continuous monitoring
    try:
        while True:
            await asyncio.sleep(UPDATE_INTERVAL)
            
            # Remove closed markets
            closed_kalshi, closed_poly = await asyncio.gather(
                kalshi.clean_markets(),
                poly.delete_markets()
            )

            embedder.delete_markets(closed_kalshi + closed_poly)
            
            # Fetch and embed new markets
            new_kalshi, new_poly = await asyncio.gather(
                kalshi.fetch_markets(),
                poly.fetch_markets()
            )
            print(new_kalshi)
            print(kalshi.last_update)
            kalshi.last_update = time.time()
            
            embedder.add_markets(new_kalshi)
            embedder.add_markets(new_poly)
            
            # Check for matches and publish as they're found
            async for match in matcher.check_new_markets(
                all_markets=embedder.all_markets,
                all_embeddings=embedder.all_embeddings
            ):
                await publisher.publish_new_match(match)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        await asyncio.gather(kalshi.close(), poly.close())
        embedder.save_embeddings()
        matcher.save_matches()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())