"""Constants for the Markets component."""

from dataclasses import dataclass

BASE_URL: str = "https://query1.finance.yahoo.com/v8/finance/chart"
HTTP_TIMEOUT: int = 15
USER_AGENT: str = "Mozilla/5.0 (compatible; MagicMirror/1.0)"


@dataclass(frozen=True, kw_only=True)
class MarketIndex:
    symbol: str  # Yahoo Finance ticker
    label: str  # short display name


# ACWI itself isn't directly tradable/quotable for free, so the iShares
# MSCI ACWI ETF (ticker ACWI) is used as the standard free-data proxy.
MARKET_INDICES: list[MarketIndex] = [
    MarketIndex(symbol="^GSPC", label="S&P 500"),
    MarketIndex(symbol="^FTSE", label="FTSE 100"),
    MarketIndex(symbol="ACWI", label="ACWI"),
]

# One fetch per symbol covers both views: the summary sparkline takes the
# most recent SUMMARY_DAYS of this, the full-screen chart uses all of it.
CHART_RANGE: str = "3mo"
CHART_INTERVAL: str = "1d"
SUMMARY_DAYS: int = 7
