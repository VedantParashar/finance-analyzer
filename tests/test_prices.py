"""yfinance is always mocked here, so the tests never touch the network."""

import pytest

from finance_analyzer import prices


def fake_yfinance(monkeypatch, fast_info):
    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        @property
        def fast_info(self):
            if isinstance(fast_info, Exception):
                raise fast_info
            return fast_info

    monkeypatch.setattr(prices.yf, "Ticker", Ticker)


def test_fetch_quote_returns_price_and_market_cap(monkeypatch):
    fake_yfinance(monkeypatch, {"lastPrice": 250.0, "marketCap": 3.7e12, "currency": "USD"})
    quote = prices.fetch_quote("AAPL")
    assert (quote.price, quote.market_cap) == (250.0, 3.7e12)


@pytest.mark.parametrize(
    "fast_info, message",
    [
        (KeyError("currentTradingPeriod"), "didn't return a price (KeyError)"),  # what an unknown symbol raises
        (ConnectionError("offline"), "didn't return a price (ConnectionError)"),
        ({"lastPrice": None, "marketCap": None, "currency": "USD"}, "no price or market cap"),
        ({"lastPrice": 250.0, "marketCap": 0, "currency": "USD"}, "no price or market cap"),
        ({"lastPrice": 250.0, "currency": "USD"}, "didn't return a price (KeyError)"),
        ({"lastPrice": 60.0, "marketCap": 2e11, "currency": "EUR"}, "in EUR, not USD"),
    ],
)
def test_fetch_quote_turns_every_failure_into_price_unavailable(monkeypatch, fast_info, message):
    fake_yfinance(monkeypatch, fast_info)
    with pytest.raises(prices.PriceUnavailable, match=message.replace("(", r"\(").replace(")", r"\)")):
        prices.fetch_quote("AAPL")


def test_fetch_exchange_rate_asks_for_the_dollar_pair(monkeypatch):
    asked = []
    fake_yfinance(monkeypatch, {"lastPrice": 32.94})
    original = prices.yf.Ticker
    monkeypatch.setattr(prices.yf, "Ticker", lambda symbol: asked.append(symbol) or original(symbol))
    rate = prices.fetch_exchange_rate("TWD")
    assert asked == ["TWD=X"] and rate.per_dollar == 32.94 and rate.fetched_at.tzinfo is not None


@pytest.mark.parametrize(
    "fast_info, message",
    [(KeyError("currentTradingPeriod"), "KeyError"), (ConnectionError("offline"), "ConnectionError"),
     ({"lastPrice": None}, "returned no US dollar to TWD rate"), ({"lastPrice": 0}, "returned no US dollar to TWD rate")],
)
def test_fetch_exchange_rate_turns_every_failure_into_price_unavailable(monkeypatch, fast_info, message):
    fake_yfinance(monkeypatch, fast_info)
    with pytest.raises(prices.PriceUnavailable, match=message):
        prices.fetch_exchange_rate("TWD")
