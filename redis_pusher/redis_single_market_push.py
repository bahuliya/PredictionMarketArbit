import asyncio
import json
from redis import asyncio as aioredis


async def main():
    redis = aioredis.from_url(
        "redis://localhost:6379", decode_responses=True, retry_on_timeout=True
    )

    msg = {
        "kalshi_ticker": "KXWOHOCKEY-MEN26CGOLD-USA",
        "poly_yes_token": "21458388471965493789661604658497971530802154496937750511773793823692388706023",
        "poly_no_token": "20451944447577875889695314888786861914178280183565267699671533375745589925341"
    }

    await redis.publish("new_matches", json.dumps(msg))
    await redis.aclose()
    print("Single match sent to Redis!")


if __name__ == "__main__":
    asyncio.run(main())