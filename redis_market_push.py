import asyncio, json
from redis import asyncio as aioredis

async def send():
    r = await aioredis.from_url("redis://localhost:6379")
    msg = {
"kalshi_ticker": "KXVENEZUELALEADER-26DEC31-EGON",
"poly_yes_token": "85482789936744260311999371350699987044247644306653001528276695717482676507600",
"poly_no_token": "70138439134789940151293221562290156019511842004756860386379046881297155754497"
    }
    await r.publish("new_matches", json.dumps(msg))
    await r.aclose()

asyncio.run(send())
