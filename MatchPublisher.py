import asyncio
import json
from typing import Dict

from redis import asyncio as aioredis


class MatchPublisher:
    def __init__(self):
        """Create a Redis publisher for match discovery events."""
        self.redis = aioredis.from_url(
            "redis://localhost:6379",
            decode_responses=True,
            retry_on_timeout=True,
        )

    @staticmethod
    def _normalize_match_payload(match_data):
        """
        Normalize payload to the schema expected by Redis listeners:
        {
            "kalshi_ticker": "...",
            "poly_yes_token": "...",
            "poly_no_token": "..."
        }
        """
        kalshi_ticker = match_data.get("kalshi_ticker")
        poly_yes_token = match_data.get("poly_yes_token")
        poly_no_token = match_data.get("poly_no_token")

        return {
            "kalshi_ticker": kalshi_ticker,
            "poly_yes_token": poly_yes_token,
            "poly_no_token": poly_no_token,
        }

    async def publish_new_match(self, match_data):
        """Publish one normalized match to the new_matches channel."""
        try:
            payload = self._normalize_match_payload(match_data)
            await self.redis.publish("new_matches", json.dumps(payload))
            print(
                "Published new match: " f"{payload['kalshi_ticker']} " f"(YES={payload['poly_yes_token']}, NO={payload['poly_no_token']})"
            )
        except Exception as exc:
            print(f"Error publishing match: {exc}")

    
    async def publish_closed_market(self, kalshi_ticker: str) -> None:
        """Publish a single closed Kalshi ticker to removed_matches."""
        try:
            await self.redis.publish("removed_matches", kalshi_ticker)
            print(f"Published removal: {kalshi_ticker}")
        except Exception as exc:
            print(f"Error publishing removal: {exc}")
    

    async def publish_closed_markets(self, closed_tickers):
        """Publish a list of closed tickers to removed_matches."""
        tasks = [self.publish_closed_market(ticker) for ticker in closed_tickers]
        if tasks:
            await asyncio.gather(*tasks)
            print(f"Published {len(tasks)} removals")