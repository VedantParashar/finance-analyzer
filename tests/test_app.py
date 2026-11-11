"""Smoke tests: run the real pages against a temporary database, with no network."""

import os
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from finance_analyzer import edgar, parse, prices, store
from finance_analyzer.parse import BalanceCheck, LineItemRow
from test_metrics import AAPL, M

APP = str(Path(__file__).parents[1] / "src" / "finance_analyzer" / "app.py")
INFO = {
    "AAPL": {"name": "Apple Inc.", "sic": 3571, "industry": "Electronic Computers"},
    "JPM": {"name": "JPMorgan Chase & Co.", "sic": 6021, "industry": "National Commercial Banks"},
    "GS": {"name": "Goldman Sachs Group Inc", "sic": 6211, "industry": "Security Brokers, Dealers & Flotation Companies"},
    "BRK-B": {"name": "Berkshire Hathaway Inc", "sic": 6331, "industry": "Fire, Marine & Casualty Insurance"},
}


def parsed_rows(ticker):
    if ticker not in INFO:
        raise ValueError(f"Unknown ticker: {ticker!r}")
    return [
        LineItemRow(item, end.isoformat(), value if item == "diluted_eps" else value * M, "accn", "")
        for end, items in AAPL.items()
        for item, value in items.items()
    ]


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.duckdb")
    monkeypatch.setattr(store, "annual_line_items", parsed_rows)
    monkeypatch.setattr(edgar, "facts_downloaded_at", lambda ticker: datetime(2020, 1, 1))  # older than any load
    # FY2026 balances, FY2025 is off by $65M; the two older years have no balance sheet at all.
    checks = [BalanceCheck("2025-09-27", False, 65 * M, False), BalanceCheck("2026-09-26", True, 0, False)]
    monkeypatch.setattr(edgar, "fetch_company_facts", lambda ticker: {})
    monkeypatch.setattr(parse, "balance_checks", lambda facts: checks)
    monkeypatch.setattr(prices, "fetch_quote", lambda ticker: prices.Quote(250.0, 3.7e12, datetime(2026, 11, 11, 15, 30)))
    monkeypatch.setattr(edgar, "fetch_company_info", lambda ticker: INFO[ticker] if ticker in INFO else parsed_rows(ticker))
    st.cache_data.clear()


def company(ticker):
    app = AppTest.from_file(APP, default_timeout=30).run()
    return app.text_input[0].input(ticker).run()


def test_empty_page_asks_for_a_ticker():
    app = AppTest.from_file(APP).run()
    assert not app.exception and "Enter a US stock ticker" in app.info[0].value


def test_company_page_loads_and_shows_every_section():
    app = company("aapl")
    assert not app.exception and not app.error
    assert store.get_company("AAPL"), "the company was saved on first view"
    assert app.header[0].value == "Apple Inc. (AAPL)"
    assert [s.value for s in app.subheader] == [
        "Line items", "Metrics for FY2026", "Valuation at today's price", "Trends", "DuPont breakdown", "Data checks"
    ]
    assert len(app.metric) == 18 + 5 + 4  # every grouped metric card, five valuation cards, four DuPont tiles
    cards = {m.label: m.value for m in app.metric}
    assert (cards["Market cap"], cards["P/E"], cards["FCF yield"]) == ("$3,700,000M", "27.99×", "3.7%")
    assert any("Share price $250.00 from Yahoo Finance" in c.value for c in app.caption)
    assert "Not available: interest_expense not reported for FY2026" in [c.value for c in app.caption]
    assert not app.warning
    assert app.get("download_button"), "Excel export offered"
    assert any("What it means" in m.value for m in app.markdown), "learning text on the cards"


def test_company_page_still_works_when_yfinance_fails(monkeypatch):
    def broken(ticker):
        raise prices.PriceUnavailable("Yahoo Finance didn't return a price (ConnectionError)")

    monkeypatch.setattr(prices, "fetch_quote", broken)
    app = company("AAPL")
    assert not app.exception and not app.error
    cards = {m.label: m.value for m in app.metric}
    assert [cards[label] for label in ("Market cap", "P/E", "P/B", "EV / EBIT", "FCF yield")] == ["unavailable"] * 5
    assert cards["Net margin"] == "27.6%", "everything else still works"
    assert any("Share price unavailable: Yahoo Finance didn't return a price" in c.value for c in app.caption)


def test_refresh_button_downloads_again_and_reloads_the_company(monkeypatch):
    app = company("AAPL")
    first_load = store.get_company("AAPL")[0].loaded_at
    refreshed = []

    def fake_refresh(ticker):
        refreshed.append(ticker)
        monkeypatch.setattr(edgar, "facts_downloaded_at", lambda ticker: datetime(2099, 1, 1))  # newer than the rows

    monkeypatch.setattr(edgar, "refresh", fake_refresh)
    app = app.button[0].click().run()
    assert not app.exception and not app.error
    assert refreshed == ["AAPL"]
    assert store.get_company("AAPL")[0].loaded_at > first_load, "rows were parsed and saved again"
    assert app.header[0].value == "Apple Inc. (AAPL)"


def test_failed_refresh_keeps_showing_the_saved_data(monkeypatch):
    def offline(ticker):
        raise httpx.ConnectError("no connection")

    monkeypatch.setattr(edgar, "refresh", offline)
    app = company("AAPL").button[0].click().run()
    assert not app.exception
    assert "Couldn't refresh from the SEC (no connection). Still showing the saved data." in app.error[0].value
    assert app.header[0].value == "Apple Inc. (AAPL)"


def test_company_page_shows_the_data_checks():
    app = company("AAPL")
    markdown = [m.value for m in app.markdown]
    assert "⚠ **Balance check:** 1 of 4 years balance, 1 doesn't, 2 couldn't be checked." in markdown
    assert "✓ **Missing years:** none, every year from FY2023 to FY2026 is stored." in markdown
    checks = app.dataframe[-1].value
    assert list(checks["Assets = liabilities + equity"]) == ["✓ Balances", "✗ Doesn't balance", "Not checked", "Not checked"]


@pytest.mark.parametrize("ticker", ["JPM", "GS", "BRK-B"])
def test_financial_company_gets_a_warning(ticker):
    app = company(ticker)
    assert not app.exception and not app.error
    assert "outside this app's scope" in app.warning[0].value


def test_unknown_ticker_shows_an_error():
    app = company("NOPE")
    assert not app.exception and "Unknown ticker" in app.error[0].value


def compare_script():
    from finance_analyzer.app import compare_page

    compare_page()


def compare(tickers):
    app = AppTest.from_function(compare_script, default_timeout=30).run()
    return app.text_input[0].input(tickers).run()


def test_compare_needs_two_to_four_tickers():
    assert "Enter 2 to 4 tickers" in compare("AAPL").info[0].value
    assert "Enter 2 to 4 tickers" in compare("AAPL KO TSLA NVDA JPM").info[0].value


def test_compare_shows_table_and_chart_for_each_company():
    app = compare("aapl, jpm")
    assert not app.exception and not app.error
    assert [s.value for s in app.subheader] == ["Latest fiscal year", "Over time"]
    table = app.dataframe[0].value
    assert list(table.columns) == ["Metric", "AAPL FY2026 (Sep 26)", "JPM FY2026 (Sep 26)"]
    assert list(table["Metric"])[-5:] == ["Market cap", "P/E", "P/B", "EV / EBIT", "FCF yield"]
    assert table.iloc[-4, 1] == "27.99×"
    assert len(app.warning) == 1  # JPM's bank banner
    assert not app.info  # same year-ends, so no note
    app = app.selectbox[0].select("free_cash_flow").run()
    assert not app.exception


def test_compare_reports_an_unknown_ticker():
    app = compare("AAPL NOPE")
    assert not app.exception and "Unknown ticker" in app.error[0].value


def test_cloud_entry_point_runs_the_same_app():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception and "Enter a US stock ticker" in app.info[0].value


def test_sec_user_agent_comes_from_secrets_before_the_environment(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "From env env@example.com")
    AppTest.from_file(APP).run()
    assert os.environ["SEC_USER_AGENT"] == "From env env@example.com", "no secret set: the environment is used"
    app = AppTest.from_file(APP)
    app.secrets["SEC_USER_AGENT"] = "From secrets secrets@example.com"
    app.run()
    assert not app.exception and os.environ["SEC_USER_AGENT"] == "From secrets secrets@example.com"
