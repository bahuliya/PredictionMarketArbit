import asyncio
import json
from pathlib import Path
from redis import asyncio as aioredis


async def main():
    redis = aioredis.from_url(
        "redis://localhost:6379", decode_responses=True, retry_on_timeout=True
    )
    json_path = Path(__file__).parent / "market_to_token" / "transformed_outputs.json"
    matches = json.loads(json_path.read_text(encoding="utf-8"))

    for i, msg in enumerate(matches, 1):
        await redis.publish("new_matches", json.dumps(msg))
        print(f"sent {i}/{len(matches)}: {msg['kalshi_ticker']}")

    await redis.aclose()
    print("All matches sent to Redis!")


if __name__ == "__main__":
    asyncio.run(main())
