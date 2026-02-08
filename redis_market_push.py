import asyncio, json
from pathlib import Path
from redis import asyncio as aioredis

async def send(msg):
    r = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    await r.publish("new_matches", json.dumps(msg))
    await r.aclose()

json_path = Path(__file__).parent / "market_to_token" / "transformed_outputs.json"
matches = json.loads(json_path.read_text(encoding="utf-8"))
for msg in matches:
    asyncio.run(send(msg))

print("ALl Matches sent to Redis!")