"""Smoke tests: run the real pages against a temporary database, with no network."""

import os
import threading
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import streamlit as st
from streamlit.proto.WidgetStates_pb2 import WidgetState
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Selectbox

from finance_analyzer import edgar, parse, peers, preload, prices, store
from finance_analyzer.parse import BalanceCheck, LineItemRow
from test_metrics import AAPL, M

APP = str(Path(__file__).parents[1] / "src" / "finance_analyzer" / "app.py")
INFO = {
    "AAPL": {"name": "Apple Inc.", "sic": 3571, "industry": "Electronic Computers"},
    "JPM": {"name": "JPMorgan Chase & Co.", "sic": 6021, "industry": "National Commercial Banks"},
    "GS": {"name": "Goldman Sachs Group Inc", "sic": 6211, "industry": "Security Brokers, Dealers & Flotation Companies"},
    "BRK-B": {"name": "Berkshire Hathaway Inc", "sic": 6331, "industry": "Fire, Marine & Casualty Insurance"},
    "SAP": {"name": "SAP SE", "sic": 7372, "industry": "Services-Prepackaged Software"},
}


COMPANIES = [edgar.Company(ticker, info["name"], f"{number:010}") for number, (ticker, info) in enumerate(INFO.items(), 1)] + [
    edgar.Company("APLE", "Apple Hospitality REIT, Inc.", "0000000099"),  # so "apple" matches two names
]


PRELOADS = []  # one entry per background pre-load started


def typed_or_picked(box):
    """What the browser sends for a search box: the text, whether picked from the list or typed in.

    AppTest's own version only accepts listed options, so it can't test typed tickers and names.
    """
    state = WidgetState()
    state.id = box.id
    if box.value is not None:
        state.string_value = str(box.format_func(box.value))
    return state


def trailing_rows(ticker):
    """The same Apple figures as if each twelve months ended three months before the fiscal year end."""
    if ticker == "SAP":
        raise parse.NoQuarterlyReports("No usable quarterly figures in the SEC's data for this company.")
    return [
        store.StoredLineItem(ticker, item, end.replace(month=6, day=27), (value if item == "diluted_eps" else value * M) * 1.1,
                             "USD", "accn", "", datetime(2026, 11, 12))
        for end, items in AAPL.items()
        for item, value in items.items()
    ]


def parsed_rows(ticker):
    return [
        LineItemRow(item, end.isoformat(), value if item == "diluted_eps" else value * M, "accn", "")
        for end, items in AAPL.items()
        for item, value in items.items()
    ]


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.duckdb")
    monkeypatch.setattr(store, "annual_line_items", parsed_rows)
    monkeypatch.setattr(store, "company_currency", lambda ticker: "EUR" if ticker == "SAP" else "USD")
    monkeypatch.setattr(edgar, "facts_downloaded_at", lambda ticker: datetime(2020, 1, 1))  # older than any load
    # FY2026 balances, FY2025 is off by $65M; the two older years have no balance sheet at all.
    checks = [BalanceCheck("2025-09-27", False, 65 * M, False), BalanceCheck("2026-09-26", True, 0, False)]
    monkeypatch.setattr(edgar, "fetch_company_facts", lambda ticker: {})
    monkeypatch.setattr(store, "trailing_twelve_months", trailing_rows)
    quarter = {"2026-03-28": (100_000 * M, False), "2026-06-27": (110_000 * M, True)}
    monkeypatch.setattr(parse, "quarterly_values", lambda facts: {"revenue": quarter, "net_income": {}})
    monkeypatch.setattr(parse, "balance_checks", lambda facts: checks)
    monkeypatch.setattr(prices, "fetch_quote", lambda ticker: prices.Quote(250.0, 3.7e12, datetime(2026, 11, 11, 15, 30)))
    monkeypatch.setattr(prices, "fetch_exchange_rate", lambda currency: prices.Rate(0.9, datetime(2026, 11, 12, 9, 0)))
    monkeypatch.setattr(edgar, "fetch_company_info", lambda ticker: INFO.get(ticker, INFO["AAPL"]))
    monkeypatch.setattr(edgar, "list_companies", lambda: COMPANIES)
    monkeypatch.setattr(preload, "run", lambda: PRELOADS.append(1))  # the hosted entry point starts it
    monkeypatch.setattr(peers, "COMPANIES", {"AAPL": [3571, 4e11], "SAP": [3571, 3e10], "GS": [3572, 5e10]})
    monkeypatch.setattr(Selectbox, "_widget_state", property(typed_or_picked))
    st.cache_data.clear()


def company(ticker):
    app = AppTest.from_file(APP, default_timeout=30).run()
    return app.selectbox[0].set_value(ticker).run()


def test_landing_page_has_a_search_box_examples_feature_tiles_and_a_footer():
    app = AppTest.from_file(APP).run()
    assert not app.exception and app.title[0].value == "Understand any public company"
    assert app.selectbox[0].label == "Search any company or ticker"
    assert app.button_group[0].options == ["AAPL"]  # the only example in the test's company list
    assert [b.label for b in app.button] == ["Analyse Apple", "Compare AAPL, MSFT, NVDA", "Learn with Coca-Cola"]
    footer = app.caption[-1].value
    assert "SEC EDGAR" in footer and "Yahoo Finance" in footer and "not investment advice" in footer
    app = app.button_group[0].set_value("AAPL").run()  # an example chip opens that company
    assert not app.exception and app.header[0].value == "Apple Inc. (AAPL)"


def test_landing_page_tiles_open_the_company_and_compare_pages():
    app = AppTest.from_file(APP).run().button[0].click().run()
    assert not app.exception and app.header[0].value == "Apple Inc. (AAPL)"
    app = AppTest.from_file(APP).run().button[1].click().run()
    assert not app.exception and app.title[0].value == "Compare"
    assert app.multiselect[0].value == ["AAPL — Apple Inc."]  # the only one in the test's company list


def test_empty_company_page_asks_for_a_company_and_offers_examples():
    app = company("AAPL").selectbox[0].set_value(None).run()
    assert not app.exception and "Search for a company" in app.info[0].value
    assert [b.label for b in app.button] == ["AAPL"]
    app = app.button[0].click().run()
    assert not app.exception and app.header[0].value == "Apple Inc. (AAPL)"


@pytest.mark.parametrize(
    "typed, header",
    [
        ("AAPL — Apple Inc.", "Apple Inc. (AAPL)"),  # a suggestion picked from the list
        ("aapl", "Apple Inc. (AAPL)"),
        ("brk.b", "Berkshire Hathaway Inc (BRK-B)"),
        ("BRK B", "Berkshire Hathaway Inc (BRK-B)"),
        ("goldman", "Goldman Sachs Group Inc (GS)"),  # the only company with that word in its name
    ],
)
def test_search_accepts_suggestions_ticker_formats_and_names(typed, header):
    app = company(typed)
    assert not app.exception and not app.error and app.header[0].value == header


def test_ambiguous_name_asks_which_company():
    app = company("apple")
    assert not app.exception and not app.header
    assert "Did you mean: **AAPL** (Apple Inc.), **APLE** (Apple Hospitality REIT, Inc.)?" in app.warning[0].value


@pytest.mark.parametrize(
    "error",
    [
        edgar.NoFinancialStatements("SPY is listed with the SEC but has no financial statements there."),
        parse.NoAnnualReports("NEWCO has no annual report (10-K) in the SEC's data."),
    ],
)
def test_fund_or_company_without_annual_reports_gets_its_own_message(monkeypatch, error):
    def fail(ticker):
        raise error

    monkeypatch.setattr(store, "annual_line_items", fail)
    app = company("AAPL")
    assert not app.exception and app.error[0].value == str(error)


def test_company_page_loads_and_shows_every_section():
    app = company("aapl")
    assert not app.exception and not app.error
    assert store.get_company("AAPL"), "the company was saved on first view"
    assert app.header[0].value == "Apple Inc. (AAPL)"
    assert [s.value for s in app.subheader] == [
        "Line items", "Metrics for FY2026", "Valuation at today's price", "Trends", "DuPont breakdown", "Red flags",
        "Peers", "Data checks",
    ]
    # every grouped metric card, five valuation cards, four DuPont tiles, four red-flag cards
    assert len(app.metric) == 18 + 5 + 4 + 4
    cards = {m.label: m.value for m in app.metric}
    assert (cards["Market cap"], cards["P/E"], cards["FCF yield"]) == ("$3,700,000M", "27.99×", "3.7%")
    assert any("Share price $250.00 from Yahoo Finance" in c.value for c in app.caption)
    assert "Not available: interest_expense not reported for FY2026" in [c.value for c in app.caption]
    assert not app.warning
    assert app.get("download_button"), "Excel export offered"
    assert any("What it means" in m.value for m in app.markdown), "learning text on the cards"
    # The test data has no cash-flow history or retained earnings, so one score works and the rest say why.
    assert cards["Accruals ratio"] == "-3.4%" and "No flag (10% or below)" in [c.value for c in app.caption]
    assert cards["Altman Z″"] == "—"
    assert "Not available: retained_earnings not reported for FY2026" in [c.value for c in app.caption]
    assert list(app.dataframe[2].value["Score"]) == ["Altman Z″", "Piotroski F", "Beneish M", "Accruals ratio"]


def test_trailing_twelve_months_view_swaps_the_figures_and_shows_the_quarters():
    app = company("aapl")
    assert list(app.dataframe[0].value.columns)[-1] == "FY2026"
    app = app.radio[0].set_value("Trailing 12 months").run()
    assert not app.exception and not app.error
    assert any("Twelve months to Jun 27, 2026" in i.value for i in app.info)
    assert list(app.dataframe[0].value.columns)[-2:] == ["12m to Jun 2025", "12m to Jun 2026"]
    assert app.dataframe[0].value.iloc[0, -1] == "$526,717M"  # revenue, 478,834 × 1.1
    assert "Metrics for 12m to Jun 2026" in [s.value for s in app.subheader]
    quarters = app.dataframe[1].value
    assert list(quarters.columns) == ["Line item", "Mar 28, 2026", "Jun 27, 2026"]
    assert list(quarters.iloc[0]) == ["Revenue", "$100,000M", "$110,000M *"]
    assert any("Profit, equity, debt and cash flow are for the 12m to Jun 2026." in c.value for c in app.caption)
    # P/E uses the twelve-month profit: 3,700,000 ÷ (132,175 × 1.1)
    assert {m.label: m.value for m in app.metric}["P/E"] == "25.45×"


def test_a_company_without_quarterly_reports_stays_on_fiscal_years():
    app = company("SAP")
    app = app.radio[0].set_value("Trailing 12 months").run()
    assert not app.exception and not app.error
    assert any("No usable quarterly figures" in i.value and "Showing fiscal years." in i.value for i in app.info)
    assert list(app.dataframe[0].value.columns)[-1] == "FY2026"


def test_industry_medians_appear_once_three_companies_in_the_group_are_stored():
    app = company("aapl")
    captions = [c.value for c in app.caption]
    assert any("No industry medians yet" in c and "starts with 35. So far: AAPL." in c for c in captions)
    assert not any(c.startswith("Industry median:") for c in captions)
    for ticker in ("SAP", "GS"):  # both are in SIC group 35 in the test's peers file
        store.load_company(ticker)
    st.cache_data.clear()
    app = company("aapl")
    captions = [c.value for c in app.caption]
    assert any("among the 3 companies loaded into this app so far" in c and "(AAPL, GS, SAP)" in c for c in captions)
    # All three hold the same test figures, so each median equals Apple's own value.
    assert "Industry median: 27.6% (3 companies)" in captions  # net margin
    assert "Industry median: 1.02× (3 companies)" in captions  # current ratio
    assert not any("Industry median: $" in c for c in captions)  # no median for free cash flow, an amount


def from_link(**params):
    app = AppTest.from_file(APP, default_timeout=30)
    for name, value in params.items():
        app.query_params[name] = value
    return app.run()


def test_a_ticker_link_opens_that_company_and_the_address_follows_the_search_box():
    app = from_link(ticker="jpm")
    assert not app.exception and app.header[0].value == "JPMorgan Chase & Co. (JPM)"
    assert app.selectbox[0].value == "JPM — JPMorgan Chase & Co." and app.query_params["ticker"] == "JPM"
    app = app.selectbox[0].set_value("AAPL").run()  # the link is only read once; after that the box decides
    assert app.header[0].value == "Apple Inc. (AAPL)" and app.query_params["ticker"] == "AAPL"
    app = app.selectbox[0].set_value(None).run()
    assert "ticker" not in app.query_params and "Search for a company" in app.info[0].value


def test_a_compare_link_opens_the_compare_page_with_those_companies():
    app = from_link(compare="AAPL, sap,AAPL")
    assert not app.exception and app.title[0].value == "Compare"
    assert app.multiselect[0].value == ["AAPL — Apple Inc.", "SAP — SAP SE"]
    assert list(app.dataframe[0].value.columns)[1:] == ["AAPL FY2026 (Sep 26)", "SAP FY2026 (Sep 26)"]
    assert app.query_params["compare"] == "AAPL,SAP"


def test_a_link_with_a_wrong_or_oversized_ticker_gets_the_usual_message():
    app = from_link(ticker="NOPE" + "X" * 500)
    assert not app.exception and "No company found for “NOPE" in app.error[0].value
    assert len(app.error[0].value) < 300  # the link's text was cut to 40 characters
    app = from_link(compare="A,B,C,D,E,F")
    assert not app.exception and len(app.multiselect[0].value) == 4


def test_the_compare_address_is_cleared_until_two_companies_are_picked():
    app = compare(["AAPL", "JPM"])
    assert app.query_params["compare"] == "AAPL,JPM"
    app = app.multiselect[0].set_value(["AAPL"]).run()
    assert "compare" not in app.query_params


def test_peers_are_suggested_and_one_click_opens_compare():
    app = company("aapl")
    buttons = {b.label: b for b in app.button}
    assert {"SAP · $30,000M", "GS · $50,000M", "Compare AAPL with the first 2"} <= buttons.keys()
    assert any("same SEC industry code as AAPL (3571, Electronic Computers), closest in revenue first" in c.value for c in app.caption)
    app = buttons["SAP · $30,000M"].click().run()
    assert not app.exception and app.title[0].value == "Compare"
    assert app.multiselect[0].value == ["AAPL — Apple Inc.", "SAP — SAP SE"]
    assert list(app.dataframe[0].value.columns)[1:] == ["AAPL FY2026 (Sep 26)", "SAP FY2026 (Sep 26)"]


def test_a_company_with_no_peers_says_so():
    app = company("JPM")
    assert not app.exception
    assert "No other company with revenue in US dollars shares JPM's SEC industry code (6021)." in [c.value for c in app.caption]


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
    assert not app.exception and "No company found for “NOPE”" in app.error[0].value


def compare_script():
    from finance_analyzer.app import compare_page

    compare_page()


def compare(tickers):
    app = AppTest.from_function(compare_script, default_timeout=30).run()
    return app.multiselect[0].set_value(tickers).run()


def test_compare_needs_at_least_two_different_companies():
    assert "Pick 2 to 4 companies" in compare(["AAPL"]).info[0].value
    assert "Pick 2 to 4 companies" in compare(["AAPL", "aapl"]).info[0].value


def test_compare_example_button_fills_the_search_box():
    app = AppTest.from_function(compare_script, default_timeout=30).run()
    assert [b.label for b in app.button] == ["AAPL vs MSFT vs NVDA", "KO vs PEP", "WMT vs COST vs TGT"]
    app = app.button[0].click().run()
    assert not app.exception and app.multiselect[0].value == ["AAPL — Apple Inc."]  # the only one in the test list


def test_compare_shows_table_and_chart_for_each_company():
    app = compare(["aapl", "JPM — JPMorgan Chase & Co."])
    assert not app.exception and not app.error
    assert [s.value for s in app.subheader] == ["Latest fiscal year", "Over time"]
    table = app.dataframe[0].value
    assert list(table.columns) == ["Metric", "AAPL FY2026 (Sep 26)", "JPM FY2026 (Sep 26)"]
    assert list(table["Metric"])[-9:] == [
        "Altman Z″", "Piotroski F", "Beneish M", "Accruals ratio", "Market cap", "P/E", "P/B", "EV / EBIT", "FCF yield",
    ]
    assert table.iloc[-4, 1] == "27.99×"
    flags = table.set_index("Metric").loc[["Altman Z″", "Piotroski F", "Beneish M", "Accruals ratio"]]
    assert list(flags.iloc[:, 0]) == ["—", "—", "—", "-3.4% · No flag"]  # the test data lacks the other inputs
    assert len(app.warning) == 1  # JPM's bank banner
    assert not app.info  # same year-ends, so no note
    app = app.selectbox[0].select("free_cash_flow").run()
    assert not app.exception


SHORT_TICKERS = [  # largest first, like the SEC's list; every one- or two-letter ticker also hides in a longer entry
    edgar.Company("MSFT", "MICROSOFT CORP", "1"),
    edgar.Company("MA", "Mastercard Inc", "2"),
    edgar.Company("META", "Meta Platforms, Inc.", "3"),
    edgar.Company("T", "AT&T INC.", "4"),
    edgar.Company("TM", "TOYOTA MOTOR CORP/", "5"),
    edgar.Company("MAR", "MARRIOTT INTERNATIONAL INC /MD/", "6"),
    edgar.Company("F", "FORD MOTOR CO", "7"),
    edgar.Company("FAST", "FASTENAL CO", "8"),
    edgar.Company("M", "Macy's, Inc.", "9"),
    edgar.Company("W", "Wayfair Inc.", "10"),
]


@pytest.mark.parametrize("typed", [c.ticker for c in SHORT_TICKERS] + ["f", "ma", "t", "m"])
def test_compare_box_offers_the_exact_ticker_first(typed):
    from finance_analyzer.app import exact_ticker_first

    options = exact_ticker_first(SHORT_TICKERS)
    # What the browser does with filter_mode="prefix": Enter picks the first entry starting with the typed text.
    first = next(text for text in options if text.lower().startswith(typed.lower()))
    assert options[first] == typed.upper()


def test_compare_box_still_suggests_companies_by_name():
    from finance_analyzer.app import exact_ticker_first

    options = exact_ticker_first(SHORT_TICKERS)
    first = next(text for text in options if text.lower().startswith("ford"))
    assert first == "FORD MOTOR CO — F" and options[first] == "F"


@pytest.mark.parametrize("typed, ticker", [("F", "F"), ("ma", "MA"), ("FORD MOTOR CO — F", "F")])
def test_compare_loads_one_and_two_letter_tickers(monkeypatch, typed, ticker):
    monkeypatch.setattr(edgar, "list_companies", lambda: COMPANIES + SHORT_TICKERS)
    app = compare(["AAPL", typed])
    assert not app.exception and not app.error
    assert list(app.dataframe[0].value.columns)[1:] == ["AAPL FY2026 (Sep 26)", f"{ticker} FY2026 (Sep 26)"]


def test_compare_reports_an_unknown_ticker():
    app = compare(["AAPL", "NOPE"])
    assert not app.exception and "No company found for “NOPE”" in app.error[0].value


def test_cloud_entry_point_runs_the_same_app_and_starts_the_pre_load_once():
    st.cache_resource.clear()
    PRELOADS.clear()
    app = AppTest.from_file(str(Path(__file__).parents[1] / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception and app.title[0].value == "Understand any public company"
    app.run()  # a second page view in the same server process
    for thread in threading.enumerate():
        if thread.name == "preload":
            thread.join(5)
    assert PRELOADS == [1]


def test_the_local_entry_point_does_not_pre_load():
    PRELOADS.clear()
    AppTest.from_file(APP, default_timeout=30).run()
    assert PRELOADS == []


def test_sec_user_agent_comes_from_secrets_before_the_environment(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "From env env@example.com")
    AppTest.from_file(APP).run()
    assert os.environ["SEC_USER_AGENT"] == "From env env@example.com", "no secret set: the environment is used"
    app = AppTest.from_file(APP)
    app.secrets["SEC_USER_AGENT"] = "From secrets secrets@example.com"
    app.run()
    assert not app.exception and os.environ["SEC_USER_AGENT"] == "From secrets secrets@example.com"


def test_foreign_filer_shows_its_currency_and_converts_market_cap_for_valuation():
    app = company("SAP")
    assert not app.exception and not app.error
    assert "SAP reports in EUR. Amounts are shown as reported" in app.info[0].value
    cards = {m.label: m.value for m in app.metric}
    assert cards["Free cash flow"] == "EUR 136,056M" and cards["Net margin"] == "27.6%"
    # $3,700,000M × 0.9 = EUR 3,330,000M; ÷ net income of 132,175M = 25.19
    assert cards["Market cap"] == "$3,700,000M" and cards["P/E"] == "25.19×"
    assert app.dataframe[0].value.iloc[0, -1] == "EUR 478,834M"  # revenue in the line-item table
    assert any("converted into EUR at 1 USD = 0.9000 EUR (Yahoo Finance, Nov 12, 2026)" in c.value for c in app.caption)
    assert any("market cap = EUR 3,330,000M" in m.value for m in app.markdown)
    assert any("EUR per US dollar = 0.9000" in m.value for m in app.markdown)


def test_foreign_valuation_is_unavailable_when_the_exchange_rate_lookup_fails(monkeypatch):
    def no_rate(currency):
        raise prices.PriceUnavailable("Yahoo Finance returned no US dollar to EUR rate")

    monkeypatch.setattr(prices, "fetch_exchange_rate", no_rate)
    app = company("SAP")
    assert not app.exception and not app.error
    cards = {m.label: m.value for m in app.metric}
    assert cards["Market cap"] == "$3,700,000M" and cards["Net margin"] == "27.6%"
    assert [cards[name] for name in ("P/E", "P/B", "EV / EBIT", "FCF yield")] == ["unavailable"] * 4
    assert any("Exchange rate unavailable: Yahoo Finance returned no US dollar to EUR rate" in c.value for c in app.caption)
    assert any("no exchange rate from US dollars to EUR" in c.value for c in app.caption)


def test_compare_notes_different_currencies():
    app = compare(["AAPL", "SAP"])
    assert not app.exception and not app.error
    assert any("report in different currencies (AAPL in USD, SAP in EUR)" in i.value for i in app.info)
    table = app.dataframe[0].value
    row = table[table["Metric"] == "Free cash flow"].iloc[0]
    assert (row.iloc[1], row.iloc[2]) == ("$136,056M", "EUR 136,056M")
    pe = table[table["Metric"] == "P/E"].iloc[0]
    assert (pe.iloc[1], pe.iloc[2]) == ("27.99×", "25.19×")  # SAP's market cap converted at 0.9
