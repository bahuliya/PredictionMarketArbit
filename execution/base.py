from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ArbitrageOpportunity:
    """
    A single detected cross-venue arbitrage hit, describing the hedge that
    would need to be placed: buy `kalshi_side` on Kalshi and the opposite
    outcome on Polymarket (`poly_asset_id`), simultaneously.
    """

    kalshi_ticker: str
    kalshi_side: str  # "yes" or "no" - the Kalshi side to BUY
    kalshi_ask: float  # dollars (0-1)
    kalshi_volume: float  # contracts available at kalshi_ask

    poly_asset_id: str  # the Polymarket token id to BUY (opposite outcome)
    poly_ask: float  # dollars (0-1)
    poly_volume: float  # contracts available at poly_ask

    contracts: float  # suggested trade size, from Arbitrage.calc_arbitrage
    roi: float  # percent
    ts: str


@dataclass(frozen=True)
class OrderRequest:
    """Generic order request passed to a venue-specific executor."""

    market_id: str  # kalshi ticker or polymarket asset id
    side: str  # "yes"/"no" for Kalshi, "buy"/"sell" for Polymarket
    price: float
    size: float
    opportunity: Optional[ArbitrageOpportunity] = None


@dataclass(frozen=True)
class OrderResult:
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None
