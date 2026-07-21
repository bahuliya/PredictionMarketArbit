import logging

from .base import OrderRequest, OrderResult

logger = logging.getLogger("execution.kalshi")


class KalshiOrderExecutor:
    """
    Places (or, for now, simulates) orders on Kalshi.

    NOT IMPLEMENTED YET: `place_order` intentionally raises until real order
    placement (REST auth + endpoint call + fill tracking) is built. Wire this
    up before ever setting ENABLE_LIVE_TRADING=1.
    """

    def __init__(self, access_key: str, private_key_pem: bytes):
        self.access_key = access_key
        self.private_key_pem = private_key_pem

    async def place_order(self, request: OrderRequest) -> OrderResult:
        logger.warning(
            "[DRY-RUN] Would place Kalshi order: %s %s @ %.4f x %.2f",
            request.market_id, request.side, request.price, request.size,
        )
        raise NotImplementedError(
            "KalshiOrderExecutor.place_order is not implemented yet - "
            "no real orders can be placed on Kalshi."
        )

    async def cancel_order(self, order_id: str) -> OrderResult:
        raise NotImplementedError("KalshiOrderExecutor.cancel_order is not implemented yet.")
