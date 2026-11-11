"""Smoke tests: run the real pages against a temporary database, with no network."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from finance_analyzer import edgar, store
from finance_analyzer.parse import LineItemRow
from test_metrics import AAPL, M

APP = str(Path(__file__).parents[1] / "src" / "finance_analyzer" / "app.py")
INFO = {
    "AAPL": {"name": "Apple Inc.", "sic": 3571, "industry": "Electronic Computers"},
    "JPM": {"name": "JPMorgan Chase & Co.", "sic": 6021, "industry": "National Commercial Banks"},
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
    assert [s.value for s in app.subheader] == ["Line items", "Metrics for FY2026", "Trends", "DuPont breakdown"]
    assert len(app.metric) == 18 + 4  # every grouped metric card plus the four DuPont tiles
    assert "Not available: interest_expense not reported for FY2026" in [c.value for c in app.caption]
    assert not app.warning
    assert any("What it means" in m.value for m in app.markdown), "learning text on the cards"


def test_bank_gets_a_warning():
    app = company("JPM")
    assert not app.exception and "outside this app's scope" in app.warning[0].value


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
    assert list(app.dataframe[0].value.columns) == ["Metric", "AAPL FY2026 (Sep 26)", "JPM FY2026 (Sep 26)"]
    assert len(app.warning) == 1  # JPM's bank banner
    assert not app.info  # same year-ends, so no note
    app = app.selectbox[0].select("free_cash_flow").run()
    assert not app.exception


def test_compare_reports_an_unknown_ticker():
    app = compare("AAPL NOPE")
    assert not app.exception and "Unknown ticker" in app.error[0].value
