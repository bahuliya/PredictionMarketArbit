import json
import logging
import traceback
import os
from arbitrage import Arbitrage
from datetime import datetime, timezone

logger = logging.getLogger("orderbook")

class Orderbook:
    def __init__(self, hub=None):
        self.kalshi_orderbook = {}
        self.polymarket_orderbook = {}
        self.matches = {}
        self.hub = hub
        self.arb_hits = {}
        self.pos_roi = {}


    def _publish(self, event):
        if self.hub is not None:
            self.hub.publish(event)

    def _utc_now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    def add_match(self, match_data):
        """
        Add a new match from Redis pub/sub
        
        match_data format:
        {
            "kalshi_ticker": "TICKER-123",
            "poly_yes_token": "abc123...",
            "poly_no_token": "abc123..."
        }
        """
        try:
            kalshi_ticker = match_data["kalshi_ticker"]
            poly_yes_token = match_data["poly_yes_token"]
            poly_no_token = match_data["poly_no_token"]
            
            # Polymarket token maps to kalshi ticker + side
            self.matches[poly_yes_token] = {
                "kalshi": kalshi_ticker,
                "kalshi_side": "no"
            }
            self.matches[poly_no_token] = {
                "kalshi": kalshi_ticker,
                "kalshi_side": "yes"
            }

            # Kalshi ticker needs to track which poly token is YES and which is NO
            self.matches[kalshi_ticker] = {
                "yes": poly_no_token,
                "no": poly_yes_token
            }

            print(f"✓ Added match: {kalshi_ticker} ↔ Poly {poly_yes_token[:8]}...")

            self._publish({
                "type": "market_added",
                "ts": self._utc_now_iso(),
                "kalshi_ticker": kalshi_ticker,
                "poly_yes_asset": poly_no_token,
                "poly_no_asset": poly_yes_token
            })

            # Return tokens for WebSocket subscription
            return {
                "kalshi": [kalshi_ticker],
                "poly": [poly_yes_token, poly_no_token]
            }
        except Exception as e:
            print(e)
            traceback.print_exc()
            os._exit(1)
    
    
    def update_kalshi_orderbook(self, data):
        try:
            data = [data]

            for m in data:
                msg_type = m.get("type")
                if msg_type is None or msg_type == "subscribed":
                    continue

                payload = m.get("msg")

                market_ticker = payload.get("market_ticker")

                yes_book = None
                no_book = None
                prev_yes = (None, None)
                prev_no = (None, None)

                if msg_type == "orderbook_snapshot":
                    logger.info("Snapshot Recieved")
                    self.kalshi_orderbook[market_ticker] = {
                        "yes": {
                            "bids": {},
                            "bestBid": None, 
                            "bestAsk": None, 
                            "bestBidVolume": 0, 
                            "bestAskVolume": 0
                        },
                        "no":  {
                            "bids": {}, 
                            "bestBid": None, 
                            "bestAsk": None, 
                            "bestBidVolume": 0, 
                            "bestAskVolume": 0
                        }
                    }

                    yes_book = self.kalshi_orderbook[market_ticker]["yes"]
                    no_book = self.kalshi_orderbook[market_ticker]["no"]

                    prev_yes = (None, None)
                    prev_no = (None, None)

                    yes_levels = payload.get("yes")
                    if yes_levels is None or yes_levels == []:
                        yes_book["bestBid"] = None
                        yes_book["bestBidVolume"] = 0
                        yes_bids = {}
                    else:
                        yes_bids = {}
                        yes_best_bid = None
                        for lvl in yes_levels:
                            yes_bids[lvl[0]] = lvl[1]
                            yes_best_bid = lvl[0]
                        yes_book["bestBid"] = yes_best_bid
                        yes_book["bestBidVolume"] = yes_bids[yes_best_bid]

                    no_levels = payload.get("no")
                    if no_levels is None or no_levels == []:
                        no_book["bestBid"] = None
                        no_book["bestBidVolume"] = 0
                        no_bids = {}
                    else:
                        no_bids = {}
                        no_best_bid = None
                        for lvl in no_levels:
                            no_bids[lvl[0]] = lvl[1]
                            no_best_bid = lvl[0]
                        no_book["bestBid"] = no_best_bid
                        no_book["bestBidVolume"] = no_bids[no_best_bid]

                    yes_book["bids"] = yes_bids
                    no_book["bids"] = no_bids
                    logger.info(self.kalshi_orderbook[market_ticker])

                elif msg_type == "orderbook_delta":
                    logger.info("Delta Recieved")
                    yes_book = self.kalshi_orderbook[market_ticker]["yes"]
                    no_book = self.kalshi_orderbook[market_ticker]["no"]

                    prev_yes = (yes_book.get("bestAsk"), yes_book.get("bestAskVolume"))
                    prev_no = (no_book.get("bestAsk"), no_book.get("bestAskVolume"))

                    side = payload["side"]
                    price = payload["price"]
                    delta = payload["delta"]

                    bids = self.kalshi_orderbook[market_ticker][side]["bids"]
                    new_qty = bids.get(price, 0) + delta

                    if new_qty <= 0:
                        if price in bids:
                            del bids[price]
                    else:
                        bids[price] = new_qty

                    book = self.kalshi_orderbook[market_ticker][side]
                    best_bid = book["bestBid"]

                    if new_qty > 0:
                        if best_bid is None or price > best_bid:
                            book["bestBid"] = price
                            book["bestBidVolume"] = new_qty
                        elif price == best_bid:
                            book["bestBidVolume"] = new_qty
                    else:
                        if best_bid is not None and price == best_bid:
                            if bids:
                                p = best_bid - 1
                                found = False

                                while p >= 0:
                                    if p in bids:
                                        book["bestBid"] = p
                                        book["bestBidVolume"] = bids[p]
                                        found = True
                                        break
                                    p -= 1

                                if not found:
                                    book["bestBid"] = None
                                    book["bestBidVolume"] = 0
                            else:
                                book["bestBid"] = None
                                book["bestBidVolume"] = 0

                # Derive asks + best asks from opposite best bids (no full asks dict needed)
                yes_book = self.kalshi_orderbook[market_ticker]["yes"]
                no_book = self.kalshi_orderbook[market_ticker]["no"]
                
                if no_book["bestBid"] is None:
                    yes_book["bestAsk"] = None
                    yes_book["bestAskVolume"] = 0
                else:
                    yes_book["bestAsk"] = 100 - no_book["bestBid"]
                    yes_book["bestAskVolume"] = no_book["bestBidVolume"]

                if yes_book["bestBid"] is None:
                    no_book["bestAsk"] = None
                    no_book["bestAskVolume"] = 0
                else:
                    no_book["bestAsk"] = 100 - yes_book["bestBid"]
                    no_book["bestAskVolume"] = yes_book["bestBidVolume"]


                if self.check_kalshi_arbitrage(prev_yes, market_ticker, "yes"):
                    print(f"Arbitrage Found: Kalshi  ------ {market_ticker}")
                if self.check_kalshi_arbitrage(prev_no, market_ticker, "no"):
                    print(f"Arbitrage Found: Kalshi  ------ {market_ticker}")
                logger.info(self.kalshi_orderbook[market_ticker])

                # publish a compact snapshot for UI
                kb = self.kalshi_orderbook.get(market_ticker)
                if kb:
                    self._publish({
                        "type": "orderbook_kalshi",
                        "ts": self._utc_now_iso(),
                        "kalshi_ticker": market_ticker,
                        "book": kb
                    })
        except Exception as e:
            print(e)
            traceback.print_exc()
            os._exit(1)
            


    def update_poly_orderbook(self, data):
        try:
            data = json.loads(data)
            # logger.info("DEBUG: Received Poly Data: " + str(data))

            if isinstance(data, list):
                event_type = data[0]["event_type"]
            else:
                event_type = data.get("event_type")

            if event_type == "book":
                logger.info("Book Recieved")
                if "bids" in data:
                    assets = [data]
                    # logger.info('DEBUG: Dict to List')
                else:
                    assets = data
                    
                for asset in assets:
                    bids = {}
                    asks = {}
        
                    for bid in asset["bids"]:
                        bids[bid["price"]] = bid["size"]
                    for ask in asset["asks"]:
                        asks[ask["price"]] = ask["size"]

                    asset_id = asset["asset_id"]
                    if asset_id in self.polymarket_orderbook:
                        prev_ask = self.polymarket_orderbook[asset_id].get("bestAsk")
                        prev_vol = self.polymarket_orderbook[asset_id].get("bestAskVolume")
                    else:
                        prev_ask = None
                        prev_vol = None

                    best_bid = asset["bids"][-1]["price"] if asset["bids"] else None
                    best_bid_vol = asset["bids"][-1]["size"] if asset["bids"] else 0
                    best_ask = asset["asks"][-1]["price"] if asset["asks"] else None
                    best_ask_vol = asset["asks"][-1]["size"] if asset["asks"] else 0
                    self.polymarket_orderbook[asset_id] = {
                        "bids": bids,
                        "asks": asks,
                        "bestBid": best_bid,
                        "bestAsk": best_ask,
                        "bestBidVolume": best_bid_vol,
                        "bestAskVolume": best_ask_vol,
                    }

                    curr_ask = self.polymarket_orderbook[asset_id]["bestAsk"]
                    curr_vol = self.polymarket_orderbook[asset_id]["bestAskVolume"]
                    logger.info(self.polymarket_orderbook[asset_id])  
                    if self.check_poly_arbitrage(prev_ask, prev_vol, curr_ask, curr_vol, asset_id):
                        print(f"Arbitrage Found: Poly ------ {asset_id}")

                    pb = self.polymarket_orderbook.get(asset_id)
                    if pb:
                        self._publish({
                            "type": "orderbook_poly",
                            "ts": self._utc_now_iso(),
                            "asset_id": asset_id,
                            "book": pb
                        })

            elif event_type == "price_change":
                logger.info("Price Change Recieved")
                for price_change in data["price_changes"]:
                    asset_id = price_change["asset_id"]
                    if asset_id not in self.polymarket_orderbook:
                        continue
                    prev_ask = self.polymarket_orderbook[asset_id]["bestAsk"]
                    prev_vol = self.polymarket_orderbook[asset_id]["bestAskVolume"]
                    price = price_change["price"]
                    size = price_change["size"]
                    side = "bids" if "BUY" == price_change["side"] else "asks"
                    asset = self.polymarket_orderbook[asset_id]
                    if size == 0:
                        del asset[side][price]
                        best_bid = price_change["best_bid"]
                        best_ask = price_change["best_ask"]
                        asset["bestBid"] = best_bid
                        asset["bestAsk"] = best_ask

                    asset[side][price] = size
                    curr_ask = self.polymarket_orderbook[asset_id]["bestAsk"]
                    curr_vol = self.polymarket_orderbook[asset_id]["bestAskVolume"]
                    if self.check_poly_arbitrage(prev_ask, prev_vol, curr_ask, curr_vol, asset_id):
                        print(f"Arbitrage Found: Poly ------ {asset_id}")
                    
                    pb = self.polymarket_orderbook.get(asset_id)
                    if pb:
                        self._publish({
                            "type": "orderbook_poly",
                            "ts": self._utc_now_iso(),
                            "asset_id": asset_id,
                            "book": pb
                        })
        except Exception as e:
            print(e)
            traceback.print_exc()
            os._exit(1)
                
    
    def check_poly_arbitrage(self, prev_ask, prev_vol, curr_ask, curr_vol, asset_id):
        try:
            #debug
            # print(self.polymarket_orderbook[asset_id])  
            if self.matches.get(asset_id) is not None:
                curr_ask = self.polymarket_orderbook[asset_id]["bestAsk"]
                curr_vol = self.polymarket_orderbook[asset_id]["bestAskVolume"]
                if (prev_ask != curr_ask or prev_vol != curr_vol) and curr_ask is not None:
                    kalshi_id = self.matches[asset_id]["kalshi"]
                    if kalshi_id not in self.kalshi_orderbook:
                        return False
                    
                    if self.matches[asset_id]["kalshi_side"] == "no":
                        kalshi_ask = self.kalshi_orderbook[kalshi_id]["no"]["bestAsk"]
                        kalshi_volume = self.kalshi_orderbook[kalshi_id]["no"]["bestAskVolume"]
                    else:
                        kalshi_ask = self.kalshi_orderbook[kalshi_id]["yes"]["bestAsk"]
                        kalshi_volume = self.kalshi_orderbook[kalshi_id]["yes"]["bestAskVolume"]
                    if kalshi_ask is None:
                        return False
                    poly_ask = self.polymarket_orderbook[asset_id]["bestAsk"]
                    poly_volume = self.polymarket_orderbook[asset_id]["bestAskVolume"]

                    hit, roi = Arbitrage.calc_arbitrage(
                    kalshi_ask / 100,
                    kalshi_volume,
                    float(poly_ask),
                    float(poly_volume))

                    if roi > 0:
                        ts = self._utc_now_iso()

                        # Always overwrite with latest positive ROI (even if smaller)
                        self.pos_roi[kalshi_id] = {"roi": float(roi), "ts": ts}
                        self._publish({
                            "type": "roi_positive",
                            "ts": ts,
                            "kalshi_ticker": kalshi_id,
                            "roi": float(roi),
                            "hit_target": bool(hit),
                        })

                        # If it hits target, also overwrite latest target-hit record
                        if hit:
                            self.arb_hits[kalshi_id] = {"roi": float(roi), "ts": ts}
                            self._publish({
                                "type": "arb_hit",
                                "ts": ts,
                                "kalshi_ticker": kalshi_id,
                                "roi": float(roi),
                            })
                        else:
                            # Clear any previous hit when falling below target
                            if kalshi_id in self.arb_hits:
                                del self.arb_hits[kalshi_id]
                    # roi <= 0: do nothing (no publish, no overwrite)
                    return bool(hit)
            return False
        except Exception as e:
            print(e)
            traceback.print_exc()
            os._exit(1)

    def check_kalshi_arbitrage(self, prev_state, kalshi_id, contract):
        try:    
            #debug
            # print(self.kalshi_orderbook[kalshi_id])
            if self.matches.get(kalshi_id) is not None:
                prev_ask, prev_vol = prev_state if isinstance(prev_state, tuple) else (prev_state, None)
                curr_ask = self.kalshi_orderbook[kalshi_id][contract]["bestAsk"]
                curr_vol = self.kalshi_orderbook[kalshi_id][contract]["bestAskVolume"]
                if (prev_ask != curr_ask or prev_vol != curr_vol) and curr_ask is not None:
                    poly_asset = self.matches[kalshi_id][contract]

                    if poly_asset not in self.polymarket_orderbook:
                        return False

                    kalshi_ask = self.kalshi_orderbook[kalshi_id][contract]["bestAsk"]
                    kalshi_volume = self.kalshi_orderbook[kalshi_id][contract]["bestAskVolume"]

                    poly_ask = self.polymarket_orderbook[poly_asset]["bestAsk"]
                    poly_volume = self.polymarket_orderbook[poly_asset]["bestAskVolume"]

                    hit, roi = Arbitrage.calc_arbitrage(
                    kalshi_ask / 100,
                    kalshi_volume,
                    float(poly_ask),
                    float(poly_volume))

                    if roi > 0:
                        ts = self._utc_now_iso()

                        # Always overwrite with latest positive ROI (even if smaller)
                        self.pos_roi[kalshi_id] = {"roi": float(roi), "ts": ts}
                        self._publish({
                            "type": "roi_positive",
                            "ts": ts,
                            "kalshi_ticker": kalshi_id,
                            "roi": float(roi),
                            "hit_target": bool(hit),
                        })

                        if hit:
                            self.arb_hits[kalshi_id] = {"roi": float(roi), "ts": ts}
                            self._publish({
                                "type": "arb_hit",
                                "ts": ts,
                                "kalshi_ticker": kalshi_id,
                                "roi": float(roi),
                            })
                        else:
                            # Clear any previous hit when falling below target
                            if kalshi_id in self.arb_hits:
                                del self.arb_hits[kalshi_id]
                    # roi <= 0: do nothing (no publish, no overwrite)
                    return bool(hit)
            return False
        except Exception as e:
            print(e)
            traceback.print_exc()
            os._exit(1)
