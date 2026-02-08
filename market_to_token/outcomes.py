import json
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---- Set paths here ----
INPUT_PATH = "parsed_candidates.json"
OUTPUT_PATH = "candidate_outcomes.json"
# ------------------------

KALSHI_BASE_URL = os.getenv("KALSHI_BASE_URL", "https://api.elections.kalshi.com/trade-api/v2")
POLY_GAMMA_BASE = os.getenv("POLY_GAMMA_BASE", "https://gamma-api.polymarket.com")


def maybe_parse_json(value: Any) -> Any:
    """Parse JSON-like strings (common for Polymarket outcomes/clobTokenIds)."""
    if isinstance(value, str):
        s = value.strip()
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return value
    return value


def fetch_kalshi_market(ticker: str, timeout: float = 15.0) -> Dict[str, Any]:
    url = f"{KALSHI_BASE_URL}/markets/{ticker}"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data.get("market", data)


def fetch_kalshi_yes_sub_title(ticker: str, timeout: float = 15.0) -> Optional[str]:
    return fetch_kalshi_market(ticker, timeout=timeout).get("yes_sub_title")


def fetch_polymarket_market(market_id: str, timeout: float = 15.0) -> Dict[str, Any]:
    url = f"{POLY_GAMMA_BASE}/markets/{market_id}"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_polymarket_outcomes_and_tokens(market_id: str, timeout: float = 15.0) -> Tuple[Any, Any]:
    m = fetch_polymarket_market(market_id, timeout=timeout)
    return maybe_parse_json(m.get("outcomes")), maybe_parse_json(m.get("clobTokenIds"))


def choose_kalshi_ticker(item: Dict[str, Any]) -> Optional[str]:
    candidates = item.get("top_5_kalshi_candidates") or []
    if not isinstance(candidates, list) or not candidates:
        return None
    return (candidates[0] or {}).get("idx")


def get_polymarket_id(item: Dict[str, Any]) -> Optional[str]:
    poly = item.get("polymarket") or {}
    idx = poly.get("idx")
    return str(idx) if idx is not None else None


def enrich_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for item in items:
        poly_id = get_polymarket_id(item)
        kalshi_ticker = choose_kalshi_ticker(item)

        enriched: Dict[str, Any] = {
            "polymarket_idx": poly_id,
            "kalshi_ticker": kalshi_ticker,
            "kalshi_yes_sub_title": None,
            "polymarket_outcomes": None,
            "polymarket_clobTokenIds": None,
        }

        if kalshi_ticker:
            try:
                enriched["kalshi_yes_sub_title"] = fetch_kalshi_yes_sub_title(kalshi_ticker)
            except requests.HTTPError as e:
                enriched["kalshi_error"] = f"HTTPError: {e.response.status_code} {e.response.text[:300]}"
            except Exception as e:
                enriched["kalshi_error"] = f"{type(e).__name__}: {e}"

        if poly_id:
            try:
                outcomes, token_ids = fetch_polymarket_outcomes_and_tokens(poly_id)
                enriched["polymarket_outcomes"] = outcomes
                enriched["polymarket_clobTokenIds"] = token_ids
            except requests.HTTPError as e:
                enriched["polymarket_error"] = f"HTTPError: {e.response.status_code} {e.response.text[:300]}"
            except Exception as e:
                enriched["polymarket_error"] = f"{type(e).__name__}: {e}"

        out.append(enriched)

    return out


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected INPUT_PATH to contain a JSON array (list) of objects.")

    enriched = enrich_items(data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(enriched)} records to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
