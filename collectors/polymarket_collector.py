import aiohttp
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

class AsyncPolymarketCollector:
    def __init__(self):
        self.base_url = "https://gamma-api.polymarket.com"
        self.path = Path.cwd() / 'data' / 'poly_categories.json'
        self.last_update_creation = None
        self.last_update_close = None
        self.session = aiohttp.ClientSession()
        self.initial_count = None
        
            
    async def fetch_markets(self):
        """Main function to fetch all markets"""
        offset = 0
        limit = 500
        total_markets = 0
        markets = []
        latest_creation_time = None
        session = self.session

        while True:
            params = {
                "limit": limit,
                "offset": offset,
                "closed": "false",
                "order": "createdAt",
                "ascending": "true",
                "include_tag": "true"
            }  
            
            if self.last_update_creation is not None:
                params["ascending"] = "false"
            
            try:
                async with session.get(f"{self.base_url}/markets", params=params) as response:
                    data = await response.json()

                    if not data:
                        print("break")
                        break
                    
                    for market in data:
                        market_id = market["id"]
                        title = market["question"]
                        description = market["description"]
                        full_text = f"{title} {description}"
                        raw_creation_time = market["createdAt"]
                        outcomes = market["outcomes"]
                        ids = market["clobTokenIds"]
                        sports = False
                        for tag in market.get("tags", []):
                            tag_num = tag.get("id")
                            if tag_num and int(tag_num) == 1:
                                sports = True
                                break

                        creation_time = datetime.fromisoformat(raw_creation_time.replace("Z", "+00:00"))
                        if self.last_update_creation is not None and creation_time <= self.last_update_creation:
                            if latest_creation_time is not None:
                                self.last_update_creation = latest_creation_time
                            print(f"Total Polymarket markets fetched: {total_markets}")
                            self.save_to_json(self.path, markets)
                            return markets
                        if latest_creation_time is None or creation_time > latest_creation_time:
                            latest_creation_time = creation_time
                        markets.append((market_id, title, full_text, 'polymarket', outcomes, ids, sports))
                    total_markets += len(data)
                    if total_markets > 0:
                        print(f"Poly: {total_markets} fetched so far!")
                    
                    if len(data) < limit:
                        break
                        
                    offset += limit
                    
            except Exception as e:
                print(f"Error fetching Polymarket markets at offset {offset}: {e}")
                break

        print(f"Initial Polymarket markets fetched: {total_markets}")
        self.last_update_creation = latest_creation_time
        self.save_to_json(self.path, markets)
        return markets
    
    async def delete_markets(self):
        offset = 0
        limit = 30
        closed_markets = []
        latest_closed_time = None

        session = self.session
        while True:
            params = {
                "limit": limit,
                "offset": offset,
                "closed": "true",
                "order": "closedTime",
                "ascending": "false"
            } 
            try:
                async with session.get(f"{self.base_url}/markets", params=params) as response:
                    
                    data = await response.json()
                    if not data:
                        break
    
                    for market in data:
                        raw_closed_time = market["closedTime"]
                        closed_time = datetime.fromisoformat(raw_closed_time.replace("Z", "+00:00"))
                        if closed_time > self.last_update_close:     
                            market_id = market["id"]
                            closed_markets.append(market_id)
                            if latest_closed_time is None or closed_time > latest_closed_time:
                                latest_closed_time = closed_time
                        else:
                            if latest_closed_time is not None:
                                self.last_update_close = latest_closed_time
                            return closed_markets
                        
                    if len(data) < limit:
                        break
                        
                    offset += limit

            except Exception as e:
                print(f"Error fetching Polymarket markets at offset {offset}: {e}")
                break

        return closed_markets
    
    def save_to_json(self, filename, markets):
        """Save markets to JSON file"""
        with open(filename, 'a') as f:
            json.dump(markets, f, indent=2)

async def main():

    client = AsyncPolymarketCollector(update_interval=20)
    await client.start()
    await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())