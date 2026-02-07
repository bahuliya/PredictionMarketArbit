import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Serves the compiled frontend from ./web/dist by default
DIST_DIR = "web/dist"

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _top_levels_from_dict(levels: Dict[Any, Any], *, descending: bool, limit: int) -> List[List[float]]:
    # levels keys might be int/str; normalize to float for JS
    parsed = []
    for p, sz in levels.items():
        try:
            pf = float(p)
            sf = float(sz)
            parsed.append([pf, sf])
        except Exception:
            continue
    parsed.sort(key=lambda x: x[0], reverse=descending)
    return parsed[:limit]

def _kalshi_side_view(kalshi_book_for_ticker: Dict[str, Any], side: str, limit: int = 250) -> Dict[str, Any]:
    """
    Kalshi UI requirement:
    - Bids: full depth (top N)
    - Asks: only the single best ask level
    Your kalshi structure stores bids; asks are implied from opposite bids. :contentReference[oaicite:0]{index=0}
    """
    this_side = kalshi_book_for_ticker.get(side) or {}
    opp_side = kalshi_book_for_ticker.get("no" if side == "yes" else "yes") or {}

    bids = this_side.get("bids") or {}
    opp_bids = opp_side.get("bids") or {}

    # Full bids depth
    bids_ladder = _top_levels_from_dict(bids, descending=True, limit=limit)

    # Only ONE ask level: use bestAsk + bestAskVolume if available,
    # otherwise derive from best opposite bid
    best_ask = this_side.get("bestAsk")
    best_ask_vol = this_side.get("bestAskVolume", 0)

    if best_ask is None:
        opp_best_bid = opp_side.get("bestBid")
        opp_best_bid_vol = opp_side.get("bestBidVolume", 0)
        if opp_best_bid is not None:
            try:
                best_ask = 100.0 - float(opp_best_bid)
                best_ask_vol = float(opp_best_bid_vol or 0)
            except Exception:
                best_ask = None

    asks_ladder = []
    if best_ask is not None:
        asks_ladder = [[float(best_ask), float(best_ask_vol or 0)]]

    return {
        "bids": bids_ladder,
        "asks": asks_ladder,
        "bestBid": None if this_side.get("bestBid") is None else float(this_side["bestBid"]),
        "bestAsk": None if best_ask is None else float(best_ask),
        "bestBidVolume": float(this_side.get("bestBidVolume", 0) or 0),
        "bestAskVolume": float(best_ask_vol or 0),
        "last": None if best_ask is None else float(best_ask),
    }


def _poly_view(poly_book_for_asset: Optional[Dict[str, Any]], limit: int = 250) -> Dict[str, Any]:
    if not poly_book_for_asset:
        return {"bids": [], "asks": [], "bestBid": None, "bestAsk": None, "bestBidVolume": 0, "bestAskVolume": 0, "last": None}

    bids = poly_book_for_asset.get("bids") or {}
    asks = poly_book_for_asset.get("asks") or {}

    best_ask = poly_book_for_asset.get("bestAsk")
    best_bid = poly_book_for_asset.get("bestBid")

    last = best_ask if best_ask is not None else best_bid

    return {
        "bids": _top_levels_from_dict(bids, descending=True, limit=limit),
        "asks": _top_levels_from_dict(asks, descending=False, limit=limit),
        "bestBid": None if best_bid is None else float(best_bid),
        "bestAsk": None if best_ask is None else float(best_ask),
        "bestBidVolume": float(poly_book_for_asset.get("bestBidVolume", 0) or 0),
        "bestAskVolume": float(poly_book_for_asset.get("bestAskVolume", 0) or 0),
        "last": None if last is None else float(last),
    }

class GuiServer:
    def __init__(self, orderbook, hub):
        self.orderbook = orderbook
        self.hub = hub
        self.app = FastAPI()
        self.clients: List[WebSocket] = []

        # API
        @self.app.websocket("/ws")
        async def ws_endpoint(ws: WebSocket):
            await ws.accept()
            self.clients.append(ws)
            try:
                await ws.send_text(json.dumps(self._initial_state()))
                while True:
                    # Keep connection alive; client doesn't need to send messages
                    await ws.receive_text()
            except WebSocketDisconnect:
                pass
            finally:
                if ws in self.clients:
                    self.clients.remove(ws)

        # Static frontend (optional)
        try:
            self.app.mount("/assets", StaticFiles(directory=f"{DIST_DIR}/assets"), name="assets")
            @self.app.get("/")
            def index():
                return FileResponse(f"{DIST_DIR}/index.html")

            @self.app.get("/market/{ticker}")
            def market_page(ticker: str):
                return FileResponse(f"{DIST_DIR}/index.html")
        except Exception:
            # If frontend isn't built yet, WS API still works
            pass

        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._broadcaster())

    def _initial_state(self) -> Dict[str, Any]:
        # Build market list from your match map on kalshi ticker keys :contentReference[oaicite:4]{index=4}
        markets = []
        for kalshi_ticker, v in self.orderbook.matches.items():
            if not isinstance(v, dict):
                continue
            if "yes" in v and "no" in v:
                hit = self.orderbook.arb_hits.get(kalshi_ticker)
                pos = self.orderbook.pos_roi.get(kalshi_ticker)
                markets.append({
                    "kalshi_ticker": kalshi_ticker,
                    "poly_yes_asset": v.get("yes"),
                    "poly_no_asset": v.get("no"),
                    "arb": hit or None,
                    "pos_roi": pos or None,
                })

        return {
            "type": "initial",
            "ts": _utc_now_iso(),
            "markets": sorted(markets, key=lambda x: x["kalshi_ticker"]),
            "orderbooks": self._snapshot_all_books(),
        }

    def _snapshot_all_books(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {"kalshi": {}, "poly": {}}

        for ticker, kb in self.orderbook.kalshi_orderbook.items():
            def _side_plain(side: Dict[str, Any]) -> Dict[str, Any]:
                bids_src = side.get("bids") or {}
                bids_plain: Dict[str, float] = {}
                for p, sz in bids_src.items():
                    try:
                        bids_plain[float(p)] = float(sz)
                    except Exception:
                        continue

                def _num(v):
                    try:
                        return None if v is None else float(v)
                    except Exception:
                        return None

                return {
                    "bids": bids_plain,
                    "bestBid": _num(side.get("bestBid")),
                    "bestAsk": _num(side.get("bestAsk")),
                    "bestBidVolume": _num(side.get("bestBidVolume")) or 0,
                    "bestAskVolume": _num(side.get("bestAskVolume")) or 0,
                }

            snap["kalshi"][ticker] = {
                "yes": _side_plain(kb.get("yes", {})),
                "no": _side_plain(kb.get("no", {})),
            }

        for asset_id, pb in self.orderbook.polymarket_orderbook.items():
            bids_src = pb.get("bids") or {}
            asks_src = pb.get("asks") or {}

            def _dict_num(src: Dict[Any, Any]) -> Dict[float, float]:
                out: Dict[float, float] = {}
                for p, sz in src.items():
                    try:
                        out[float(p)] = float(sz)
                    except Exception:
                        continue
                return out

            snap["poly"][asset_id] = {
                "bids": _dict_num(bids_src),
                "asks": _dict_num(asks_src),
                "bestBid": None if pb.get("bestBid") is None else float(pb["bestBid"]),
                "bestAsk": None if pb.get("bestAsk") is None else float(pb["bestAsk"]),
                "bestBidVolume": float(pb.get("bestBidVolume", 0) or 0),
                "bestAskVolume": float(pb.get("bestAskVolume", 0) or 0),
            }

        return snap

    async def _broadcast(self, msg: Dict[str, Any]) -> None:
        if not self.clients:
            return
        data = json.dumps(msg)
        dead = []
        for c in self.clients:
            try:
                await c.send_text(data)
            except Exception:
                dead.append(c)
        for c in dead:
            if c in self.clients:
                self.clients.remove(c)

    async def _broadcaster(self):
        while True:
            event = await self.hub.queue.get()
            await self._broadcast(event)

def build_gui_app(orderbook, hub) -> FastAPI:
    return GuiServer(orderbook, hub).app
