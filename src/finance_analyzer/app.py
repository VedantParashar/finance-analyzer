"""The Streamlit UI. It only displays what the metrics engine computes.

Run from the project folder: uv run --env-file .env finance-analyzer
"""

import html
import os
import threading
from datetime import timedelta
from pathlib import Path

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finance_analyzer import charts, display, edgar, export, parse, peers, preload, prices, store
from finance_analyzer.metrics import FORMULA_TEXT, MIN_FOR_MEDIAN, Metric, company_metrics, industry_medians, price_metrics

YEARS_SHOWN = 5
ANNUAL, TTM = "Fiscal years", "Trailing 12 months"
PAGES: dict[str, object] = {}  # filled by run(); lets one page send the user to another


def use_secret_user_agent() -> None:
    """Prefer SEC_USER_AGENT from Streamlit secrets (how hosted apps get settings) over the environment."""
    try:
        user_agent = st.secrets.get("SEC_USER_AGENT")
    except FileNotFoundError:  # no secrets file at all, the normal case on your own computer
        return
    if user_agent:
        os.environ["SEC_USER_AGENT"] = user_agent  # edgar.py reads it from here and stays free of Streamlit
EXAMPLES = ["AAPL", "MSFT", "NVDA", "KO", "WMT", "TSLA"]
COMPARE_EXAMPLES = [["AAPL", "MSFT", "NVDA"], ["KO", "PEP"], ["WMT", "COST", "TGT"]]
STYLE = Path(__file__).with_name("style.css").read_text()
REIT_SIC = 6798  # SEC code for real estate investment trusts
QUOTE_MINUTES = 15  # how long a share price is reused before asking Yahoo Finance again


# Kept for a day at most, so a long-running app still notices when the SEC files on disk get too old.
@st.cache_data(ttl=timedelta(days=1), show_spinner=False)  # load_or_explain() shows a spinner naming the company
def load(ticker: str) -> tuple[list[store.StoredLineItem], dict, dict]:
    """Rows, metrics by year and company info, (re)loading the company if the SEC download is newer."""
    info = edgar.fetch_company_info(ticker)  # also rejects unknown tickers before any parsing
    downloaded = edgar.facts_downloaded_at(ticker)  # downloads again by itself after 7 days
    rows = store.get_company(ticker)
    if not rows or rows[0].loaded_at < downloaded:
        store.load_company(ticker)
        rows = store.get_company(ticker)
    return rows, company_metrics(rows), info


@st.cache_data(ttl=timedelta(days=1), show_spinner=False)
def balance_checks(ticker: str) -> list[parse.BalanceCheck]:
    """The balance check for each year, from the SEC download already cached on disk by load()."""
    # Re-reads the facts because the check needs the reported balance sheet total, which isn't a stored item.
    return parse.balance_checks(edgar.fetch_company_facts(ticker))


@st.cache_data(ttl=timedelta(days=1), show_spinner="Building the last twelve months…")
def trailing(ticker: str) -> tuple[list[store.StoredLineItem], dict, dict]:
    """Rows and metrics for the trailing twelve months, and the single quarters behind them."""
    rows = store.trailing_twelve_months(ticker)
    return rows, company_metrics(rows), parse.quarterly_values(edgar.fetch_company_facts(ticker))


def sic_code(ticker: str) -> int:
    """A stored company's SIC code: from the peers file when it's there (no download), else from the SEC."""
    if ticker in peers.COMPANIES:
        return peers.COMPANIES[ticker][0]
    try:
        return edgar.fetch_company_info(ticker)["sic"]
    except (httpx.HTTPError, ValueError, RuntimeError):
        return 0


# `viewing` is only part of the cache key: a company seen for the first time has just been saved and must count.
@st.cache_data(ttl=timedelta(days=1), show_spinner=False)
def industry(group: int, viewing: str) -> tuple[list[str], dict[str, tuple[float, int]]]:
    """The stored companies whose SIC code starts with these two digits, and the median of each of their metrics."""
    tickers = [ticker for ticker in store.stored_tickers() if sic_code(ticker) // 100 == group]
    latest = []
    for ticker in tickers:
        metrics = company_metrics(store.get_company(ticker))
        latest.append(metrics[max(metrics)])  # each company's latest fiscal year
    return tickers, industry_medians(latest)


# Only successes are cached: an exception passes straight through, so the next page run tries again.
@st.cache_data(ttl=QUOTE_MINUTES * 60, show_spinner=False)
def quote(ticker: str) -> prices.Quote:
    return prices.fetch_quote(ticker)


@st.cache_data(ttl=QUOTE_MINUTES * 60, show_spinner=False)
def exchange_rate(currency: str) -> prices.Rate:
    return prices.fetch_exchange_rate(currency)


def valuation(ticker: str, rows: list[store.StoredLineItem]) -> tuple[dict[str, Metric], str]:
    """The price-based metrics, and a sentence saying where the price (and exchange rate) came from."""
    try:
        latest = quote(ticker)
    except prices.PriceUnavailable as error:
        return price_metrics(rows, None), f"Share price unavailable: {error}. The rest of the page doesn't need it."
    note = f"Share price ${latest.price:,.2f} from Yahoo Finance, fetched {latest.fetched_at:%b %-d, %Y at %H:%M} UTC."
    currency = display.currency(rows)
    if currency == "USD":
        return price_metrics(rows, latest.market_cap), note
    try:
        rate = exchange_rate(currency)
    except prices.PriceUnavailable as error:
        return price_metrics(rows, latest.market_cap), f"{note} Exchange rate unavailable: {error}."
    return price_metrics(rows, latest.market_cap, rate.per_dollar), (
        f"{note} Market cap is converted into {currency} at 1 USD = {rate.per_dollar:,.4f} {currency} "
        f"(Yahoo Finance, {rate.fetched_at:%b %-d, %Y})."
    )


def option(company: edgar.Company) -> str:
    """How a company reads in the search box."""
    return f"{company.ticker} — {company.name}"


def exact_ticker_first(companies: list[edgar.Company]) -> dict[str, str]:
    """Compare-box text → ticker, ordered so that typing a ticker and pressing Enter picks that ticker.

    The box picks the first entry that starts with the typed text. With the shortest tickers first, the
    first entry starting with "F" is "F — Ford": no shorter ticker exists and "FAST — …" comes later.
    Every company is listed a second time name first, so typing "Coca" still suggests Coca-Cola.
    """
    by_ticker = {option(c): c.ticker for c in sorted(companies, key=lambda c: len(c.ticker))}  # stable: largest first
    return by_ticker | {f"{c.name} — {c.ticker}": c.ticker for c in companies}


@st.cache_data(ttl=timedelta(days=1), show_spinner=False)
def company_options(exact_first: bool = False) -> dict[str, str]:
    """Search-box text → ticker for every company the SEC lists, largest first unless exact_first."""
    companies = edgar.list_companies()
    return exact_ticker_first(companies) if exact_first else {option(c): c.ticker for c in companies}


def options_or_explain(exact_first: bool = False) -> dict[str, str] | None:
    """The search box's suggestions, or None after showing why the SEC's company list couldn't be read."""
    try:
        return company_options(exact_first)
    except RuntimeError as error:  # no SEC_USER_AGENT
        st.error(str(error))
    except httpx.HTTPError as error:
        st.error(f"Couldn't reach the SEC ({error}). Check your connection and try again.")
    return None


def ticker_or_explain(choice: str, options: dict[str, str]) -> str | None:
    """The SEC's ticker for a picked suggestion or for typed text, or None after showing what to try."""
    if choice in options:
        return options[choice]
    company = edgar.find_ticker(choice)  # typed text: BRK.B, brk b and BRK-B all find BRK-B
    if company:
        return company.ticker
    matches = edgar.search_companies(choice)
    if len(matches) == 1:
        return matches[0].ticker
    if matches:
        names = ", ".join(f"**{match.ticker}** ({match.name})" for match in matches)
        st.warning(f"No ticker is exactly “{choice}”. Did you mean: {names}? Pick one from the list.")
    else:
        st.error(
            f"No company found for “{choice}”. Check the spelling, or try the company's name. Only companies "
            "that file with the US SEC are covered."
        )
    return None


def from_link(text: str) -> str:
    """Search-box text for a ticker taken from a link: the listed entry when it's an exact ticker."""
    text = text.strip()[:40]  # a link is outside input: keep it short, then treat it like typed text
    try:
        company = edgar.find_ticker(text)
    except (httpx.HTTPError, RuntimeError):  # the page itself will explain what's wrong
        return text
    return option(company) if company else text


def open_from_link() -> None:
    """Act once on ?ticker=AAPL or ?compare=AAPL,KO, so a shared link opens straight on that view."""
    if st.session_state.get("link_opened"):
        return
    st.session_state["link_opened"] = True
    if "compare" in st.query_params:
        tickers = [text for text in st.query_params["compare"].split(",") if text.strip()]
        st.session_state["compare"] = list(dict.fromkeys(map(from_link, tickers)))[:4]  # the box holds four at most
        st.switch_page(PAGES["compare"])
    elif "ticker" in st.query_params:
        open_company(from_link(st.query_params["ticker"]))


def choose(key: str, value) -> None:
    st.session_state[key] = value


def load_or_explain(ticker: str):
    """load(), or None after showing the user why it failed."""
    try:
        with st.spinner(f"Loading {ticker} from SEC EDGAR… (the first time takes a few seconds)"):
            return load(ticker)
    except (ValueError, RuntimeError) as error:  # fund, no annual reports, or no SEC_USER_AGENT
        st.error(str(error))
    except httpx.HTTPError as error:
        st.error(f"Couldn't reach the SEC ({error}). Check your connection and try again.")
    return None


def bank_banner(ticker: str, info: dict) -> None:
    if edgar.is_financial(info["sic"]):
        st.warning(
            f"{ticker} is classified as {info['industry']} (SIC {info['sic']}). Banks, brokers and insurers are "
            "outside this app's scope: ratios like gross margin, current ratio and ROIC don't apply to them, so many "
            "show as unavailable and the rest need care."
        )


def refresh_button(ticker: str) -> None:
    if st.button("Refresh", icon=":material/refresh:", help="Download this company's filings from the SEC again and reload it."):
        try:
            edgar.refresh(ticker)
        except (httpx.HTTPError, RuntimeError) as error:
            st.error(f"Couldn't refresh from the SEC ({error}). Still showing the saved data.")
        else:
            st.cache_data.clear()  # load() then sees a download newer than the stored rows and reloads them
            st.rerun()


def metric_card(
    name: str, metric: Metric, prior: Metric | None, currency: str, benchmark: tuple[float, int] | None = None,
    history: list[float | None] | None = None,
) -> None:
    with st.container(border=True, height="stretch"):  # cards in a row share the tallest one's height
        st.metric(
            display.LABELS[name],
            display.format_metric(name, metric.value, currency),
            delta=display.yoy_delta(name, metric.value, prior.value if prior else None),
            delta_color="inverse" if name == "debt_to_equity" else "normal",
            chart_data=sparkline(history),
        )
        if name in display.RED_FLAGS and metric.value is not None:
            st.caption(display.verdict(name, metric.value))
        if benchmark:
            st.caption(f"Industry median: {display.format_metric(name, benchmark[0])} ({benchmark[1]} companies)")
        if metric.reason:
            st.caption(f"Not available: {metric.reason}")
        # The long text lives in a popover, so every card in a row keeps the same height.
        with st.popover("How it's calculated", icon=":material/info:", type="tertiary"):
            st.markdown(f"**Formula:** {FORMULA_TEXT[name]}")
            for key, value in metric.inputs.items():
                st.markdown(f"- {key.replace('_', ' ')} = {display.format_input(key, value, currency)}")
            if metric.value is not None:
                st.markdown(f"= **{display.format_metric(name, metric.value, currency)}**")
            for note in metric.notes:
                st.caption(f"ⓘ {note}")
            learn(name)


def financial_table(table: list[dict[str, str]], unit: str | None = None) -> None:
    """A table of figures: first column pinned (with the unit in its header), numbers right-aligned,
    negatives, already in parentheses, in red."""
    frame = pd.DataFrame(table)
    first = frame.columns[0]
    config = {first: st.column_config.TextColumn(f"{first} · {unit}" if unit else first, pinned=True)}
    config |= {column: st.column_config.TextColumn(alignment="right") for column in frame.columns[1:]}
    # One red that reads on the light and the dark background (DESIGN.md: red means down or negative).
    styled = frame.style.map(lambda text: "color: #EF4444" if str(text).startswith("(") else "")
    st.dataframe(styled, hide_index=True, column_config=config, height="content")  # every row, no inner scroll


def learn(name: str) -> None:
    text = display.LEARNING[name]
    st.markdown(f"**What it means:** {text['meaning']}")
    st.markdown(f"**What's good:** {text['good']}")
    st.markdown(f"**Common traps:** {text['traps']}")


def trend_chart(title: str, labels: list[str], series: dict[str, list], kind: str, tickformat: str) -> go.Figure:
    """Bars or lines over the years; None values show as gaps, never as zero."""
    trace = go.Bar if kind == "bar" else go.Scatter
    figure = go.Figure([trace(name=name, x=labels, y=values) for name, values in series.items()])
    return charts.style(figure, tickformat, title)


def sparkline(values: list[float | None] | None) -> list[float] | None:
    """The values a card's sparkline draws: missing years left out, and none at all for fewer than two."""
    shown = [value for value in values or [] if value is not None]
    return shown if len(shown) > 1 else None


def company_page() -> None:
    options = options_or_explain()
    if options is None:
        return
    choice = st.selectbox(
        "Company",
        options,
        index=None,
        placeholder="Search any company or ticker, e.g. AAPL or Apple",
        accept_new_options=True,
        label_visibility="collapsed",
        key="company",
    )
    if not choice:
        st.title("Company")
        st.info("Search for a company to see five years of statements and ratios from its SEC filings.")
        st.markdown("**Popular examples**")
        for column, example in zip(st.columns(len(EXAMPLES)), EXAMPLES):
            company = edgar.find_ticker(example)
            if company:
                column.button(example, help=company.name, on_click=choose, args=("company", option(company)))
        st.query_params.pop("ticker", None)
        return
    ticker = ticker_or_explain(choice, options)
    if ticker is None:
        return
    loaded = load_or_explain(ticker)
    if loaded is None:
        return
    rows, metrics, info = loaded
    st.query_params["ticker"] = ticker  # the browser's address now links straight to this company
    st.set_page_config(page_title=f"{ticker} · {info['name']} · Datadough")  # the browser tab names the company
    company_header(ticker, info, rows, metrics)

    currency = display.currency(rows)
    if currency != "USD":
        st.info(
            f"{ticker} reports in {currency}. Amounts are shown as reported and aren't converted to US dollars. "
            "For the valuation ratios, the market cap (in dollars) is converted into "
            f"{currency} at today's exchange rate."
        )
    bank_banner(ticker, info)

    annual_rows, quarters = rows, None
    period = st.segmented_control(
        "Period", [ANNUAL, TTM], default=ANNUAL, required=True, key="period",
        help="Trailing 12 months (TTM) adds up the last four quarters, so it includes results reported since "
        "the last annual report.",
    )
    if period == TTM:
        try:
            rows, metrics, quarters = trailing(ticker)
        except parse.NoQuarterlyReports as error:
            st.info(f"{error} Showing fiscal years.")
    name_period = display.twelve_months if quarters is not None else display.fiscal_year
    years = sorted(metrics)[-YEARS_SHOWN:]
    labels = [name_period(end) for end in years]
    if quarters is not None:
        note = (
            f"Twelve months to {years[-1]:%b %-d, %Y}, compared with the same twelve months in earlier years. "
            "Income and cash flow items add up four quarters; balance sheet items are as of that date. "
            "Where a message says “FY”, read it as the twelve months ending in that year."
        )
        if years[-1] == max(row.fiscal_year_end for row in annual_rows):
            note += " The latest report is the annual one, so these match the latest fiscal year."
        st.info(note)
    in_industry, medians = industry(info["sic"] // 100, ticker) if info["sic"] else ([], {})

    overview, financials, ratios, flags, value, checks = st.tabs(
        ["Overview", "Financials", "Ratios", "Red flags", "Valuation", "Data checks"]
    )
    with overview:
        overview_tab(ticker, info, rows, metrics, years, labels, currency, medians)
    with financials:
        financials_tab(rows, years, name_period, quarters, currency)
    with ratios:
        ratios_tab(info, rows, metrics, years, labels, currency, in_industry, medians)
    with flags:
        red_flags_section(metrics, years, labels, currency, info, medians)
    with value:
        valuation_tab(ticker, rows, labels, currency, quarters is not None)
    with checks:
        data_checks_section(ticker, annual_rows)


def company_header(ticker: str, info: dict, rows: list[store.StoredLineItem], metrics: dict) -> None:
    """Name, ticker, exchange and industry, today's price, and the actions; it stays put while scrolling."""
    with st.container(key="company-header"):
        left, right = st.columns([1, 1], vertical_alignment="center")
        with left:
            st.header(f"{info['name']} ({ticker})", anchor=False)
            with st.container(horizontal=True, gap="small"):
                for text in filter(None, [info.get("exchange"), f"SIC {info['sic']} · {info['industry']}"]):
                    st.badge(text, color="gray")
        with right, st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
            price_tile(ticker)
            refresh_button(ticker)
            st.download_button(
                "Excel",
                export.company_workbook(ticker, rows, metrics, reit=info["sic"] == REIT_SIC),
                file_name=f"{ticker}_financials.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                icon=":material/download:",
                help="Download the statements and ratios as an Excel workbook with live formulas.",
            )
            with st.popover("Share", icon=":material/share:"):
                base = (st.context.url or "").split("?")[0]
                st.code(f"{base}?ticker={ticker}", language=None)
                st.caption("Anyone with this link opens this company's page.")


def price_tile(ticker: str) -> None:
    """Today's share price and change, or a short note when Yahoo Finance has none."""
    try:
        latest = quote(ticker)
    except prices.PriceUnavailable:
        st.caption("Share price unavailable")
        return
    change = None
    if latest.previous_close:
        move = latest.price - latest.previous_close
        change = f"{move:+,.2f} ({move / latest.previous_close:+.2%}) today"
    st.metric("Share price", f"${latest.price:,.2f}", delta=change, width="content")


def overview_tab(
    ticker: str, info: dict, rows: list[store.StoredLineItem], metrics: dict, years: list, labels: list[str],
    currency: str, medians: dict,
) -> None:
    st.caption(
        f"The headline numbers for {labels[-1]}"
        + (f", with the change from {labels[-2]} and the last {len(years)} years as a sparkline." if len(labels) > 1 else ".")
    )
    by_key = {(row.item, row.fiscal_year_end): row.value for row in rows}
    latest, prior = metrics[years[-1]], metrics[years[-2]] if len(years) > 1 else {}
    kpis = st.columns(4)
    for column, (label, item) in zip(kpis, [("Revenue", "revenue"), ("Net income", "net_income")]):
        values = [by_key.get((item, end)) for end in years]
        with column.container(border=True, height="stretch"):
            st.metric(
                label,
                display.money(values[-1], currency) if values[-1] is not None else "—",
                delta=display.yoy_delta("free_cash_flow", values[-1], values[-2] if len(values) > 1 else None),
                chart_data=sparkline(values),
            )
    for column, name in zip(kpis[2:], ["operating_margin", "free_cash_flow"]):
        with column:
            metric_card(name, latest[name], prior.get(name), currency, medians.get(name),
                        [metrics[end][name].value for end in years])

    chart, snapshot = st.columns([3, 2])
    by_million = {key: value / 1e6 for key, value in by_key.items()}
    chart.plotly_chart(
        trend_chart(
            f"Revenue and net income ({display.symbol(currency)}M)",
            labels,
            {label: [by_million.get((item, end)) for end in years] for label, item in
             [("Revenue", "revenue"), ("Net income", "net_income")]},
            "bar",
            "$,.0f" if currency == "USD" else ",.0f",
        )
    )
    with snapshot:
        st.subheader("Key ratios vs industry")
        financial_table(display.ratio_snapshot(latest, medians, labels[-1]))
        if not medians:
            st.caption("No industry median yet: it needs more companies from this industry loaded into the app.")
    peers_section(ticker, info)


def financials_tab(rows: list[store.StoredLineItem], years: list, name_period, quarters: dict | None, currency: str) -> None:
    st.caption("The line items behind every ratio, as reported in the annual reports (10-K, 20-F or 40-F).")
    table, derivations = display.line_item_table(rows, years, name_period)
    financial_table(table, display.table_unit(currency))
    if derivations:
        with st.expander("\\* Values we calculated rather than read straight from the filing"):
            st.markdown("\n".join(f"- {line}" for line in derivations))
    if quarters is not None:
        with st.expander("The single quarters behind these figures"):
            financial_table(display.quarterly_table(quarters, currency), display.table_unit(currency))
            st.caption(
                "\\* Calculated. Companies report some items only for the year so far, so a quarter is that figure "
                "minus the quarters before it. The fourth quarter is never reported on its own: it is the full "
                "year minus the first nine months. Columns are quarter end dates."
            )


def ratios_tab(
    info: dict, rows: list[store.StoredLineItem], metrics: dict, years: list, labels: list[str], currency: str,
    in_industry: list[str], medians: dict,
) -> None:
    st.subheader(f"Metrics for {labels[-1]}")
    st.caption(f"Changes are against {labels[-2]}." if len(labels) > 1 else "No prior year stored.")
    if medians:
        st.caption(
            f"Industry median: the middle value among the {len(in_industry)} companies loaded into this app so far "
            f"whose SEC industry code starts with {info['sic'] // 100} ({', '.join(in_industry)}), each for its "
            "latest fiscal year. It is a small sample, not the whole industry."
        )
    else:
        st.caption(
            f"No industry medians yet: they need at least {MIN_FOR_MEDIAN} companies loaded into this app whose SEC "
            f"industry code starts with {info['sic'] // 100}. So far: {', '.join(in_industry) or 'none'}."
        )
    latest, prior = metrics[years[-1]], metrics[years[-2]] if len(years) > 1 else {}
    for group, names in display.GROUPS.items():
        st.markdown(f"**{group}**")
        for column, name in zip(st.columns(4), names):
            with column:
                metric_card(name, latest[name], prior.get(name), currency, medians.get(name),
                            [metrics[end][name].value for end in years])

    if info["sic"] == REIT_SIC:
        st.markdown("**Real estate (REIT)**")
        st.caption(
            "Real estate investment trusts report funds from operations (FFO) as their main earnings measure. "
            "Ratios built for other companies (current ratio, gross margin) often don't apply to them."
        )
        for column, name in zip(st.columns(4), display.REIT_METRICS):
            with column:
                metric_card(name, latest[name], prior.get(name), currency, None,
                            [metrics[end][name].value for end in years])

    st.subheader("Trends")
    left, right = st.columns(2)
    left.plotly_chart(
        trend_chart(
            "Margins",
            labels,
            {display.LABELS[name]: [metrics[end][name].value for end in years] for name in display.GROUPS["Profitability"]},
            "line",
            ".0%",
        )
    )
    right.plotly_chart(
        trend_chart("Return on equity", labels, {"ROE": [metrics[end]["roe"].value for end in years]}, "line", ".0%")
    )
    dupont_section(metrics, years, labels)


def valuation_tab(ticker: str, rows: list[store.StoredLineItem], labels: list[str], currency: str, twelve_months: bool) -> None:
    valuation_metrics, price_note = valuation(ticker, rows)
    st.caption(
        f"{price_note} Profit, equity, debt and cash flow are for the {labels[-1]}." if twelve_months else
        f"{price_note} Profit, equity, debt and cash flow are from {labels[-1]}, the last full fiscal year, so "
        "these differ from sites that use the last twelve months."
    )
    for column, name in zip(st.columns(5), display.PRICE_METRICS):
        with column:
            metric_card(name, valuation_metrics[name], None, currency)


def open_company(text: str) -> None:
    """Fill the company page's search box with this text and go there."""
    st.session_state["company"] = text
    st.switch_page(PAGES["company"])


def open_compare(tickers: list[str]) -> None:
    """Fill the compare page's search box with these tickers and go there."""
    found = [company for company in map(edgar.find_ticker, tickers) if company]
    st.session_state["compare"] = [option(company) for company in found]
    st.switch_page(PAGES["compare"])


def peers_section(ticker: str, info: dict) -> None:
    st.subheader("Peers")
    own = edgar.find_ticker(ticker)
    share_classes = {c.ticker for c in edgar.list_companies() if c.cik == own.cik}  # GOOGL and GOOG are one company
    suggested = peers.suggest(share_classes, info["sic"])
    if not suggested:
        st.caption(f"No other company with revenue in US dollars shares {ticker}'s SEC industry code ({info['sic']}).")
        return
    ranked = "closest in revenue first" if share_classes & peers.COMPANIES.keys() else "largest first"
    st.caption(
        f"Companies with the same SEC industry code as {ticker} ({info['sic']}, {info['industry']}), {ranked}. "
        f"Revenue is for fiscal {peers.REVENUE_YEAR}. Click one to compare it with {ticker}."
    )
    for column, peer in zip(st.columns(len(suggested)), suggested):
        company = edgar.find_ticker(peer.ticker)
        note = "" if peer.same_code else f" Wider industry group ({info['sic'] // 10}x), not the same code."
        if column.button(
            f"{peer.ticker} · {display.money(peer.revenue)}", key=f"peer-{peer.ticker}",
            help=f"{company.name if company else peer.ticker}.{note}",
        ):
            open_compare([ticker, peer.ticker])
    if len(suggested) > 1 and st.button(f"Compare {ticker} with the first {min(3, len(suggested))}"):
        open_compare([ticker] + [peer.ticker for peer in suggested[:3]])


def data_checks_section(ticker: str, rows: list[store.StoredLineItem]) -> None:
    st.caption(
        "Two checks on the downloaded data, for every year stored (not just the five shown elsewhere): "
        "does the balance sheet add up, and is any year missing? The oldest year usually can't be checked: "
        "a company's first filings in this format repeat earlier income statements but not the balance sheet. "
        f"SEC data loaded {rows[0].loaded_at:%b %-d, %Y at %H:%M} UTC; it refreshes by itself once it's "
        f"{edgar.MAX_AGE.days} days old."
    )
    table = display.balance_check_table(rows, balance_checks(ticker))
    gaps = display.missing_years(sorted({row.fiscal_year_end for row in rows}))
    results = [line["Assets = liabilities + equity"] for line in table]
    balanced, failed = sum(r.startswith("✓") for r in results), sum(r.startswith("✗") for r in results)
    unchecked = len(table) - balanced - failed
    st.markdown(
        f"{'⚠' if failed else '✓'} **Balance check:** {balanced} of {len(table)} years balance, {failed} "
        f"{'doesn\'t' if failed == 1 else 'don\'t'}, {unchecked} couldn't be checked."
    )
    with st.expander("Balance check by year", expanded=bool(failed)):
        st.dataframe(table, hide_index=True)
    if gaps:
        st.markdown(f"⚠ **Missing years:** {len(gaps)} gap{'s' if len(gaps) > 1 else ''}.")
        st.markdown("\n".join(f"- {line}" for line in gaps))
    else:
        first, last = table[-1]["Fiscal year"], table[0]["Fiscal year"]
        st.markdown(f"✓ **Missing years:** none, every year from {first} to {last} is stored.")


def red_flags_section(metrics: dict, years: list, labels: list[str], currency: str, info: dict, medians: dict) -> None:
    st.caption(
        "Four well-known screens for financial trouble or low-quality earnings. They are prompts to read the "
        "annual report more closely, not verdicts: each one misfires on some kinds of company (see "
        "“Common traps” in each card)."
    )
    if edgar.is_financial(info["sic"]):
        st.caption("These scores were built for industrial and commercial companies and don't apply to banks, brokers or insurers.")
    for column, name in zip(st.columns(4), display.RED_FLAGS):
        with column:
            metric_card(name, metrics[years[-1]][name], None, currency, medians.get(name),
                        [metrics[end][name].value for end in years])
    table = []
    for name in display.RED_FLAGS:
        line = {"Score": display.LABELS[name]}
        for label, end in zip(labels, years):
            value = metrics[end][name].value
            line[label] = display.short_verdict(name, value)
        table.append(line)
    financial_table(table)


def dupont_section(metrics: dict, years: list, labels: list[str]) -> None:
    st.subheader("DuPont breakdown")
    with st.popover("How it's calculated", icon=":material/info:", type="tertiary"):
        st.markdown(f"**Formula:** {FORMULA_TEXT['dupont']}")
        learn("dupont")
    dupont = metrics[years[-1]]["dupont"]
    if dupont.value is None:
        st.caption(f"Not available for {labels[-1]}: {dupont.reason}")
    else:
        factors = st.columns(4)
        factors[0].metric("Net margin", f"{dupont.inputs['net margin']:.1%}")
        factors[1].metric("× Asset turnover", f"{dupont.inputs['asset turnover']:.2f}×")
        factors[2].metric("× Equity multiplier", f"{dupont.inputs['equity multiplier']:.2f}×")
        factors[3].metric("= ROE", f"{dupont.value:.1%}")

    table = []
    for key, text in [("net margin", "{:.1%}"), ("asset turnover", "{:.2f}×"), ("equity multiplier", "{:.2f}×")]:
        line = {"Factor": key.capitalize()}
        for label, end in zip(labels, years):
            metric = metrics[end]["dupont"]
            line[label] = text.format(metric.inputs[key]) if metric.value is not None else "—"
        table.append(line)
    table.append({"Factor": "ROE", **{label: display.format_metric("dupont", metrics[end]["dupont"].value)
                                      for label, end in zip(labels, years)}})
    financial_table(table)


def compare_page() -> None:
    st.title("Compare")
    options = options_or_explain(exact_first=True)
    if options is None:
        return
    choices = st.multiselect(
        "Companies (2 to 4)",
        options,
        max_selections=4,
        placeholder="Type tickers or company names, e.g. AAPL, Coca-Cola",
        accept_new_options=True,
        select_all=False,  # otherwise Enter on "AAPL" picks "Select 632 matches": four look-alike companies
        # Matching from the start of each entry is what lets an exact ticker win: see exact_ticker_first().
        filter_mode="prefix",
        key="compare",
    )
    if not choices:
        st.info("Pick 2 to 4 companies to see their ratios, red-flag scores and valuation side by side.")
        st.markdown("**Popular comparisons**")
        for column, example in zip(st.columns(len(COMPARE_EXAMPLES)), COMPARE_EXAMPLES):
            found = [company for company in map(edgar.find_ticker, example) if company]
            column.button(" vs ".join(example), on_click=choose, args=("compare", [option(c) for c in found]))
        st.query_params.pop("compare", None)
        return
    resolved = [ticker_or_explain(choice, options) for choice in choices]
    if None in resolved:
        return
    tickers = list(dict.fromkeys(resolved))  # the same company picked twice counts once
    if not 2 <= len(tickers) <= 4:
        st.info(f"Pick 2 to 4 companies. Add at least one more to compare with {tickers[0]}.")
        st.query_params.pop("compare", None)
        return
    st.set_page_config(page_title=f"{' vs '.join(tickers)} · Datadough")  # the browser tab names the comparison
    st.query_params["compare"] = ",".join(tickers)  # the browser's address now links straight to this comparison
    companies = {}
    for ticker in tickers:
        loaded = load_or_explain(ticker)
        if loaded is None:
            return
        companies[ticker] = loaded
        bank_banner(ticker, loaded[2])

    latest_ends = {ticker: max(metrics) for ticker, (_, metrics, _) in companies.items()}
    currencies = {ticker: display.currency(rows) for ticker, (rows, _, _) in companies.items()}
    mixed = len(set(currencies.values())) > 1
    if mixed:
        each = ", ".join(f"{ticker} in {currency}" for ticker, currency in currencies.items())
        st.info(
            f"These companies report in different currencies ({each}) and their amounts aren't converted. Ratios "
            "compare fairly, including the valuation ratios (market cap is converted at today's exchange rate); "
            "amounts such as free cash flow don't."
        )
    note = display.year_end_note(latest_ends)
    if note:
        st.info(note)

    colours = dict(zip(companies, charts.SERIES))  # one colour per company: chip, table column and chart line
    company_chips({ticker: info["name"] for ticker, (_, _, info) in companies.items()}, colours)

    st.subheader("Latest fiscal year")
    columns = {ticker: f"{ticker} {display.fiscal_year(end)} ({end:%b %-d})" for ticker, end in latest_ends.items()}
    names = [name for group in display.GROUPS.values() for name in group]
    latest = {
        ticker: {**metrics[latest_ends[ticker]], **valuation(ticker, rows)[0]}
        for ticker, (rows, metrics, _) in companies.items()
    }
    table, marks, missing = [], [], []
    for name in names + display.RED_FLAGS + display.PRICE_METRICS:
        line = {"Metric": display.LABELS[name]}
        for ticker in companies:
            metric = latest[ticker][name]
            if name in display.RED_FLAGS:
                line[columns[ticker]] = display.short_verdict(name, metric.value)
            else:
                line[columns[ticker]] = display.format_metric(name, metric.value, currencies[ticker])
            if metric.reason:
                missing.append(f"{display.LABELS[name]}, {ticker}: {metric.reason}")
        table.append(line)
        comparable = not (mixed and name in display.DOLLARS)  # amounts in different currencies
        best, worst = display.best_worst(name, {t: latest[t][name].value for t in companies}) if comparable else (None, None)
        marks.append({columns[best]: "best", columns[worst]: "worst"} if best else {})
    compare_table(table, marks, {columns[ticker]: colour for ticker, colour in colours.items()})
    st.caption(
        "Best and worst in each row are in green and red, where higher or lower is clearly better (market cap, "
        "the equity multiplier and the red-flag scores aren't ranked). The four rows before the last five are red-flag scores "
        "(prompts to look closer, not verdicts; see the company page for each one's meaning). The last five use "
        "today's share price from Yahoo Finance; the rest come from the annual reports."
    )
    if missing:
        with st.expander("Why some values are missing"):
            st.markdown("\n".join(f"- {line}" for line in missing))

    st.subheader("Over time")
    group = st.segmented_control("Group", list(display.GROUPS), default="Profitability", required=True, key="chart_group")
    name = st.pills(
        "Metric", display.GROUPS[group], default=display.GROUPS[group][0], required=True,
        format_func=display.LABELS.get, key=f"chart_metric_{group}",
    )
    scale = 1e6 if name in display.DOLLARS else 1  # free cash flow in millions
    figure = go.Figure()
    for ticker, (_, metrics, _) in companies.items():
        years = sorted(metrics)[-YEARS_SHOWN:]
        values = [metrics[end][name].value for end in years]
        figure.add_scatter(
            name=ticker, x=years, y=[None if v is None else v / scale for v in values], mode="lines+markers",
            line_color=colours[ticker],
        )
    charts.style(figure, ".2f" if name in display.MULTIPLES else ",.0f" if name in display.DOLLARS else ".0%")
    # Real year-end dates on the x-axis, so different fiscal calendars line up honestly.
    figure.update_layout(height=380, xaxis_title="Fiscal year end")
    figure.update_yaxes(
        title=(
            None if name not in display.DOLLARS
            else "millions, each in its own currency" if mixed
            else f"{display.symbol(next(iter(currencies.values())))}M"
        ),
    )
    st.plotly_chart(figure)


def company_chips(names: dict[str, str], colours: dict[str, str]) -> None:
    """One chip per company, with the colour it has in the table and the chart."""
    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;padding:4px 12px;margin:0 8px 8px 0;'
        f'border:1px solid rgba(100,116,139,0.3);border-radius:999px;font-size:0.9rem">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:{colours[ticker]}"></span>'
        f"<b>{ticker}</b>&nbsp;{html.escape(name)}</span>"
        for ticker, name in names.items()
    )
    st.html(f"<div>{chips}</div>")


def compare_table(table: list[dict[str, str]], marks: list[dict[str, str]], colours: dict[str, str]) -> None:
    """The compare table: each company's column tinted with its colour, best and worst in a row marked."""
    frame = pd.DataFrame(table)

    def style(row):
        return [
            f"background-color: {colours[column]}14; "  # 14 = 8% opacity: a tint in the light and dark theme
            + {"best": "color: #22A55A; font-weight: 600", "worst": "color: #EF4444; font-weight: 600"}.get(
                marks[row.name].get(column), ""
            )
            if column in colours else ""
            for column in frame.columns
        ]

    config = {"Metric": st.column_config.TextColumn(pinned=True)}
    config |= {column: st.column_config.TextColumn(alignment="right") for column in colours}
    st.dataframe(frame.style.apply(style, axis=1), hide_index=True, column_config=config, height="content")


def home_page() -> None:
    with st.container(key="hero"):
        st.badge("Datadough · free and open source, for students", color="primary")
        st.title("Understand any public company")
        st.markdown(
            "Five years of a company's own SEC filings turned into ratios, trends and red flags, "
            "each explained in plain English."
        )
        options = options_or_explain()
        if options is None:
            return
        choice = st.selectbox(
            "Search any company or ticker",
            options,
            index=None,
            placeholder="Search any company or ticker, e.g. AAPL or Coca-Cola",
            accept_new_options=True,
            label_visibility="collapsed",
            key="home_search",
        )
        examples = [ticker for ticker in EXAMPLES if edgar.find_ticker(ticker)]
        picked = st.pills("Try", examples, key="home_example")
    if choice or picked:
        open_company(choice or option(edgar.find_ticker(picked)))

    tiles = [
        ("Analyse", ":material/query_stats:", "Statements and 18 metrics over five years, by fiscal year or the "
         "last twelve months, with the industry median next to each.", "Analyse Apple",
         lambda: open_company(option(edgar.find_ticker("AAPL")))),
        ("Compare", ":material/compare_arrows:", "Put 2 to 4 companies side by side: ratios, red-flag scores and "
         "valuation, best and worst marked.", "Compare AAPL, MSFT, NVDA",
         lambda: open_compare(["AAPL", "MSFT", "NVDA"])),
        ("Learn", ":material/school:", "Every number shows its formula filled in with the company's own figures, "
         "what it means, what's good and the common traps.", "Learn with Coca-Cola",
         lambda: open_company(option(edgar.find_ticker("KO")) if edgar.find_ticker("KO") else "KO")),
    ]
    for column, (title, icon, text, action, go_to) in zip(st.columns(3), tiles):
        with column.container(border=True, height="stretch"):
            st.markdown(f"#### {icon} {title}")
            st.markdown(text)
            if st.button(action, key=f"tile-{title}", type="tertiary", icon=":material/arrow_forward:", icon_position="right"):
                go_to()


def footer() -> None:
    st.divider()
    st.caption(
        "Data: financial statements from [SEC EDGAR](https://www.sec.gov/edgar) (XBRL company facts, as filed); "
        "share prices and exchange rates from Yahoo Finance, through yfinance. Figures can contain errors, so check "
        "the filing before relying on one. For learning only, **not investment advice**. "
        "[Open source on GitHub](https://github.com/VedantParashar/finance-analyzer)."
    )


@st.cache_resource(show_spinner=False)  # once per server process, however many people open the app
def start_preload() -> threading.Thread:
    """Start loading the stress-test companies in the background; the page doesn't wait for it."""
    thread = threading.Thread(target=preload.run, name="preload", daemon=True)
    thread.start()
    return thread


def run(preload_companies: bool = False) -> None:
    st.set_page_config(page_title="Datadough", page_icon=":material/query_stats:", layout="wide")
    st.html(f"<style>{STYLE}</style>")  # the few rules config.toml can't express, see DESIGN.md
    use_secret_user_agent()
    if preload_companies:
        start_preload()
    PAGES["home"] = st.Page(home_page, title="Home", icon=":material/home:", default=True)
    PAGES["company"] = st.Page(company_page, title="Company", icon=":material/business:")
    PAGES["compare"] = st.Page(compare_page, title="Compare", icon=":material/compare_arrows:")
    page = st.navigation(list(PAGES.values()), position="top")
    open_from_link()
    page.run()
    footer()


# Streamlit runs this file as __main__; importing it (as the tests do) only defines the pages.
if __name__ == "__main__":
    run()
