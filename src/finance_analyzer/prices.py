"""Today's share price and market cap from Yahoo Finance, through the yfinance package.

Yahoo has no official API: yfinance reads the same pages a browser does, so it can break or be
blocked at any time. Every failure becomes PriceUnavailable, and the app carries on without prices.
"""

from datetime import UTC, datetime
from typing import NamedTuple

import yfinance as yf


class Quote(NamedTuple):
    price: float  # last traded price of one share, in dollars
    market_cap: float  # price × shares outstanding, in dollars
    fetched_at: datetime  # UTC


class PriceUnavailable(Exception):
    """Yahoo Finance gave no usable price; the message says why."""


def fetch_quote(ticker: str) -> Quote:
    try:
        info = yf.Ticker(ticker).fast_info
        price, market_cap, currency = info["lastPrice"], info["marketCap"], info["currency"]
    except Exception as error:  # yfinance raises many unrelated types (KeyError, HTTP errors, rate limits)
        raise PriceUnavailable(f"Yahoo Finance didn't return a price ({type(error).__name__})") from error
    if not price or not market_cap or price <= 0 or market_cap <= 0:
        raise PriceUnavailable("Yahoo Finance returned no price or market cap")
    if currency != "USD":  # the statements are in dollars, so a ratio against another currency would be wrong
        raise PriceUnavailable(f"Yahoo Finance quotes this share in {currency}, not USD")
    return Quote(float(price), float(market_cap), datetime.now(UTC))
