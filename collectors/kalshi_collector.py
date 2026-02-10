import aiohttp
import asyncio
import json
from pathlib import Path
import time

URL = "https://api.elections.kalshi.com/trade-api/v2"

class AsyncKalshiCollector:

    def __init__(self):
        self.url = URL
        self.last_update = None
        self.session = aiohttp.ClientSession()
        self.save_path = Path.cwd() / 'data' / 'kalshi_categories.json'
        self.initial_count = None

    async def clean_markets(self):
        
        page = 0 
        s_market_count = 0
        cursor = None
        settled_tickers = []

        # Use persistent session
        session = self.session
        while True:
            page += 1
            params = {
                'limit': 1000,
                'status': 'closed',
            }
            
            # Only add min_settled_ts if last_update exists and is not None
            if self.last_update is not None:
                # Convert to integer timestamp (API expects int, not float)
                params['min_settled_ts'] = int(self.last_update)

            if cursor:
                params['cursor'] = cursor

            try:
                async with session.get(f"{self.url}/markets", params=params) as response:
                    data = await response.json()
                    markets = data.get('markets', [])

                    if not markets:
                        break

                    for market in markets:
                        s_market_count += 1
                        settled_tickers.append(market['ticker'])

                    cursor = data.get('cursor')
                    
                    if not cursor:
                        break

            except Exception as e:
                print(f"Error fetching closed markets page {page}: {e}")
                break

        return settled_tickers

            
    async def fetch_markets(self):
        page = 0
        total_markets = 0
        cursor = None
        new_markets = []
        punc = ['.', '?', '!']

        session = self.session

        while True:
            page += 1

            params = {
                'limit': 1000,
                'status': 'open',
                'mve_filter' : 'exclude',
            }

            if self.last_update is not None:
                params['min_created_ts'] = self.last_update

            if cursor:
                params['cursor'] = cursor

            try:
                async with session.get(f"{self.url}/markets", params=params) as response:
                    data = await response.json()
                    markets = data.get('markets', [])

                    for market in markets:
                        ticker = market['ticker']
                        title = market['title']
                        rules_primary = market['rules_primary']
                        rules_secondary = market.get('rules_secondary', '')
                        yes_sub_title = market.get('yes_sub_title', '')
                        no_sub_title = market.get('no_sub_title', '')
                        
                        if title and title[-1] not in punc:
                            title += '.'

                        full_description = f"{title} {rules_primary} {rules_secondary}"
                        new_markets.append((ticker, title, full_description, 'kalshi', yes_sub_title, no_sub_title))

                    total_markets += len(markets)
                    if total_markets > 0:
                        print(f"Kalshi: {total_markets} fetched so far!")
                    cursor = data.get('cursor')
                    
                    if not cursor:
                        break

            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                await session.close()
                break 
        
        # Set markets once after all pages are fetched
        print(f"Total Kalshi markets fetched: {total_markets}")
        return new_markets
        
    async def save_to_json(self, data, filename):
        with open(filename, 'a') as f:
            json.dump(data, f, indent=4)

    
async def main():

    client = AsyncKalshiCollector(update_interval=5)
    await client.start()
    await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())