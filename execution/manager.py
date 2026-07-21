import asyncio
import logging
from typing import List, Optional

from .base import ArbitrageOpportunity, OrderRequest

logger = logging.getLogger("execution.manager")


class ExecutionManager:
    """
    Central hook that Orderbook notifies whenever an arbitrage target is hit.

    Disabled (dry-run/log-only) by default. Real order placement only runs if
    BOTH `live_trading_enabled=True` is passed in AND the venue executors have
    working `place_order` implementations (they don't yet - see
    kalshi_executor.py / polymarket_executor.py. Those intentionally raise
    NotImplementedError so this can't accidentally trade real money).
    """

    def __init__(self, kalshi_executor=None, poly_executor=None, live_trading_enabled: bool = False):
        self.kalshi_executor = kalshi_executor
        self.poly_executor = poly_executor
        self.live_trading_enabled = live_trading_enabled
        self.opportunities: List[ArbitrageOpportunity] = []

        if self.live_trading_enabled:
            logger.warning(
                "ExecutionManager started with live_trading_enabled=True - orders will be "
                "attempted for every arb_hit (executors are currently unimplemented stubs, "
                "so calls will fail loudly until place_order is actually implemented)."
            )
        else:
            logger.info("ExecutionManager running in dry-run mode (no orders will be placed).")

    def on_arb_hit(self, opportunity: ArbitrageOpportunity) -> None:
        """Sync entrypoint, safe to call directly from Orderbook. Never raises."""
        self.opportunities.append(opportunity)
        logger.info(
            "ARB HIT %s: BUY kalshi-%s @ %.4f (%.2f avail) + poly %s @ %.4f (%.2f avail) "
            "-> size %.2f contracts, roi=%.2f%%",
            opportunity.kalshi_ticker, opportunity.kalshi_side, opportunity.kalshi_ask,
            opportunity.kalshi_volume, opportunity.poly_asset_id, opportunity.poly_ask,
            opportunity.poly_volume, opportunity.contracts, opportunity.roi,
        )

        if not self.live_trading_enabled:
            return

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._execute(opportunity))
        except RuntimeError:
            logger.error(
                "No running event loop; cannot schedule order execution for %s",
                opportunity.kalshi_ticker,
            )

    async def _execute(self, opportunity: ArbitrageOpportunity) -> None:
        kalshi_req = OrderRequest(
            market_id=opportunity.kalshi_ticker,
            side=opportunity.kalshi_side,
            price=opportunity.kalshi_ask,
            size=opportunity.contracts,
            opportunity=opportunity,
        )
        poly_req = OrderRequest(
            market_id=opportunity.poly_asset_id,
            side="buy",
            price=opportunity.poly_ask,
            size=opportunity.contracts,
            opportunity=opportunity,
        )

        try:
            if self.kalshi_executor is not None:
                await self.kalshi_executor.place_order(kalshi_req)
            if self.poly_executor is not None:
                await self.poly_executor.place_order(poly_req)
        except NotImplementedError as e:
            logger.error("Order execution not implemented yet: %s", e)
        except Exception:
            logger.exception("Unexpected error executing arbitrage for %s", opportunity.kalshi_ticker)
