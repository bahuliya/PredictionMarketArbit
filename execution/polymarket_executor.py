import logging

from .base import OrderRequest, OrderResult

logger = logging.getLogger("execution.polymarket")


class PolymarketOrderExecutor:
    """
    Places (or, for now, simulates) orders on Polymarket's CLOB.

    NOT IMPLEMENTED YET: `place_order` intentionally raises until real order
    placement (py-clob-client auth/signing + endpoint call + fill tracking)
    is built. Wire this up before ever setting ENABLE_LIVE_TRADING=1.
    """

    def __init__(self, private_key: str = None, funder_address: str = None):
        self.private_key = private_key
        self.funder_address = funder_address

    async def place_order(self, request: OrderRequest) -> OrderResult:
        logger.warning(
            "[DRY-RUN] Would place Polymarket order: %s %s @ %.4f x %.2f",
            request.market_id, request.side, request.price, request.size,
        )
        raise NotImplementedError(
            "PolymarketOrderExecutor.place_order is not implemented yet - "
            "no real orders can be placed on Polymarket."
        )

    async def cancel_order(self, order_id: str) -> OrderResult:
        raise NotImplementedError("PolymarketOrderExecutor.cancel_order is not implemented yet.")
