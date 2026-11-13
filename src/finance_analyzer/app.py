"""The Streamlit UI. It only displays what the metrics engine computes.

Run from the project folder: uv run --env-file .env finance-analyzer
"""

import os
from datetime import timedelta

import httpx
import plotly.graph_objects as go
import streamlit as st

from finance_analyzer import display, edgar, export, parse, peers, prices, store
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
QUOTE_MINUTES = 15  # how long a share price is reused before asking Yahoo Finance again


# Kept for a day at most, so a long-running app still notices when the SEC files on disk get too old.
@st.cache_data(ttl=timedelta(days=1), show_spinner="Loading from SEC EDGAR…")
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
        st.session_state["company"] = from_link(st.query_params["ticker"])


def choose(key: str, value) -> None:
    st.session_state[key] = value


def load_or_explain(ticker: str):
    """load(), or None after showing the user why it failed."""
    try:
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


def refresh_button(ticker: str, rows: list[store.StoredLineItem]) -> None:
    if st.button("Refresh data", help="Download this company's filings from the SEC again and reload it."):
        try:
            edgar.refresh(ticker)
        except (httpx.HTTPError, RuntimeError) as error:
            st.error(f"Couldn't refresh from the SEC ({error}). Still showing the saved data.")
        else:
            st.cache_data.clear()  # load() then sees a download newer than the stored rows and reloads them
            st.rerun()
    st.caption(
        f"SEC data loaded {rows[0].loaded_at:%b %-d, %Y at %H:%M} UTC. It refreshes by itself once it's "
        f"{edgar.MAX_AGE.days} days old."
    )


def metric_card(
    name: str, metric: Metric, prior: Metric | None, currency: str, benchmark: tuple[float, int] | None = None
) -> None:
    with st.container(border=True):
        st.metric(
            display.LABELS[name],
            display.format_metric(name, metric.value, currency),
            delta=display.yoy_delta(name, metric.value, prior.value if prior else None),
            delta_color="inverse" if name == "debt_to_equity" else "normal",
        )
        if name in display.RED_FLAGS and metric.value is not None:
            st.caption(display.verdict(name, metric.value))
        if benchmark:
            st.caption(f"Industry median: {display.format_metric(name, benchmark[0])} ({benchmark[1]} companies)")
        if metric.reason:
            st.caption(f"Not available: {metric.reason}")
        for note in metric.notes:
            st.caption(f"ⓘ {note}")
        with st.expander("Formula and meaning"):
            st.markdown(f"**Formula:** {FORMULA_TEXT[name]}")
            for key, value in metric.inputs.items():
                st.markdown(f"- {key.replace('_', ' ')} = {display.format_input(key, value, currency)}")
            if metric.value is not None:
                st.markdown(f"= **{display.format_metric(name, metric.value, currency)}**")
            learn(name)


def learn(name: str) -> None:
    text = display.LEARNING[name]
    st.markdown(f"**What it means:** {text['meaning']}")
    st.markdown(f"**What's good:** {text['good']}")
    st.markdown(f"**Common traps:** {text['traps']}")


def trend_chart(title: str, labels: list[str], series: dict[str, list], kind: str, tickformat: str) -> go.Figure:
    """Bars or lines over the years; None values show as gaps, never as zero."""
    trace = go.Bar if kind == "bar" else go.Scatter
    figure = go.Figure([trace(name=name, x=labels, y=values) for name, values in series.items()])
    figure.update_layout(title=title, height=320, margin={"t": 40, "b": 20}, legend={"orientation": "h"})
    figure.update_yaxes(tickformat=tickformat)
    return figure


def company_page() -> None:
    st.title("Company")
    options = options_or_explain()
    if options is None:
        return
    choice = st.selectbox(
        "Company",
        options,
        index=None,
        placeholder="Type a ticker or a company name, e.g. AAPL or Apple",
        accept_new_options=True,
        key="company",
    )
    if not choice:
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

    st.header(f"{info['name']} ({ticker})")
    st.caption(info["industry"])
    currency = display.currency(rows)
    if currency != "USD":
        st.info(
            f"{ticker} reports in {currency}. Amounts are shown as reported and aren't converted to US dollars. "
            "For the valuation ratios, the market cap (in dollars) is converted into "
            f"{currency} at today's exchange rate."
        )
    bank_banner(ticker, info)
    st.download_button(
        "Download Excel with live formulas",
        export.company_workbook(ticker, rows, metrics),
        file_name=f"{ticker}_financials.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    refresh_button(ticker, rows)

    annual_rows, quarters = rows, None
    period = st.radio(
        "Period", [ANNUAL, TTM], horizontal=True, key="period",
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
    latest = metrics[years[-1]]
    prior = metrics[years[-2]] if len(years) > 1 else {}

    st.subheader("Line items")
    table, derivations = display.line_item_table(rows, years, name_period)
    st.dataframe(table, hide_index=True)
    if derivations:
        with st.expander("\\* Values we calculated rather than read straight from the filing"):
            st.markdown("\n".join(f"- {line}" for line in derivations))
    if quarters is not None:
        with st.expander("The single quarters behind these figures"):
            st.dataframe(display.quarterly_table(quarters, currency), hide_index=True)
            st.caption(
                "\\* Calculated. Companies report some items only for the year so far, so a quarter is that figure "
                "minus the quarters before it. The fourth quarter is never reported on its own: it is the full "
                "year minus the first nine months. Columns are quarter end dates."
            )

    st.subheader(f"Metrics for {labels[-1]}")
    st.caption(f"Changes are against {labels[-2]}." if len(labels) > 1 else "No prior year stored.")
    in_industry, medians = industry(info["sic"] // 100, ticker) if info["sic"] else ([], {})
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
    for group, names in display.GROUPS.items():
        st.markdown(f"**{group}**")
        for column, name in zip(st.columns(4), names):
            with column:
                metric_card(name, latest[name], prior.get(name), currency, medians.get(name))

    st.subheader("Valuation at today's price")
    valuation_metrics, price_note = valuation(ticker, rows)
    st.caption(
        f"{price_note} Profit, equity, debt and cash flow are for the {labels[-1]}." if quarters is not None else
        f"{price_note} Profit, equity, debt and cash flow are from {labels[-1]}, the last full fiscal year, so "
        "these differ from sites that use the last twelve months."
    )
    for column, name in zip(st.columns(5), display.PRICE_METRICS):
        with column:
            metric_card(name, valuation_metrics[name], None, currency)

    st.subheader("Trends")
    by_key = {(row.item, row.fiscal_year_end): row.value / 1e6 for row in rows}
    left, right = st.columns(2)
    left.plotly_chart(
        trend_chart(
            f"Revenue and net income ({display.symbol(currency)}M)",
            labels,
            {label: [by_key.get((item, end)) for end in years] for label, item in
             [("Revenue", "revenue"), ("Net income", "net_income")]},
            "bar",
            "$,.0f" if currency == "USD" else ",.0f",
        )
    )
    right.plotly_chart(
        trend_chart(
            "Margins",
            labels,
            {display.LABELS[name]: [metrics[end][name].value for end in years] for name in display.GROUPS["Profitability"]},
            "line",
            ".0%",
        )
    )
    left.plotly_chart(
        trend_chart("Return on equity", labels, {"ROE": [metrics[end]["roe"].value for end in years]}, "line", ".0%")
    )

    dupont_section(metrics, years, labels)
    red_flags_section(metrics, years, labels, currency, info, medians)
    peers_section(ticker, info)
    data_checks_section(ticker, annual_rows)


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
    st.subheader("Data checks")
    st.caption(
        "Two checks on the downloaded data, for every year stored (not just the five shown above): "
        "does the balance sheet add up, and is any year missing? The oldest year usually can't be checked: "
        "a company's first filings in this format repeat earlier income statements but not the balance sheet."
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
    st.subheader("Red flags")
    st.caption(
        "Four well-known screens for financial trouble or low-quality earnings. They are prompts to read the "
        "annual report more closely, not verdicts: each one misfires on some kinds of company (see "
        "“Common traps” in each card)."
    )
    if edgar.is_financial(info["sic"]):
        st.caption("These scores were built for industrial and commercial companies and don't apply to banks, brokers or insurers.")
    for column, name in zip(st.columns(4), display.RED_FLAGS):
        with column:
            metric_card(name, metrics[years[-1]][name], None, currency, medians.get(name))
    table = []
    for name in display.RED_FLAGS:
        line = {"Score": display.LABELS[name]}
        for label, end in zip(labels, years):
            value = metrics[end][name].value
            line[label] = "—" if value is None else f"{display.format_metric(name, value)} · {display.verdict(name, value).split(' (')[0].split(':')[0]}"
        table.append(line)
    st.dataframe(table, hide_index=True)


def dupont_section(metrics: dict, years: list, labels: list[str]) -> None:
    st.subheader("DuPont breakdown")
    with st.expander("Formula and meaning"):
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
    st.dataframe(table, hide_index=True)


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
        st.markdown("**Popular comparisons**")
        for column, example in zip(st.columns(len(COMPARE_EXAMPLES)), COMPARE_EXAMPLES):
            found = [company for company in map(edgar.find_ticker, example) if company]
            column.button(" vs ".join(example), on_click=choose, args=("compare", [option(c) for c in found]))
    resolved = [ticker_or_explain(choice, options) for choice in choices]
    if None in resolved:
        return
    tickers = list(dict.fromkeys(resolved))  # the same company picked twice counts once
    if not 2 <= len(tickers) <= 4:
        st.info("Pick 2 to 4 companies.")
        st.query_params.pop("compare", None)
        return
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

    st.subheader("Latest fiscal year")
    columns = {ticker: f"{ticker} {display.fiscal_year(end)} ({end:%b %-d})" for ticker, end in latest_ends.items()}
    names = [name for group in display.GROUPS.values() for name in group]
    latest = {
        ticker: {**metrics[latest_ends[ticker]], **valuation(ticker, rows)[0]}
        for ticker, (rows, metrics, _) in companies.items()
    }
    table, missing = [], []
    for name in names + display.PRICE_METRICS:
        line = {"Metric": display.LABELS[name]}
        for ticker in companies:
            metric = latest[ticker][name]
            line[columns[ticker]] = display.format_metric(name, metric.value, currencies[ticker])
            if metric.reason:
                missing.append(f"{display.LABELS[name]}, {ticker}: {metric.reason}")
        table.append(line)
    st.dataframe(table, hide_index=True)
    st.caption("The last five rows use today's share price from Yahoo Finance; the rest come from the annual reports.")
    if missing:
        with st.expander("Why some values are missing"):
            st.markdown("\n".join(f"- {line}" for line in missing))

    st.subheader("Over time")
    name = st.selectbox("Metric", names, format_func=display.LABELS.get)
    scale = 1e6 if name in display.DOLLARS else 1  # free cash flow in millions
    figure = go.Figure()
    for ticker, (_, metrics, _) in companies.items():
        years = sorted(metrics)[-YEARS_SHOWN:]
        values = [metrics[end][name].value for end in years]
        figure.add_scatter(
            name=ticker, x=years, y=[None if v is None else v / scale for v in values], mode="lines+markers"
        )
    # Real year-end dates on the x-axis, so different fiscal calendars line up honestly.
    figure.update_layout(height=380, margin={"t": 20}, xaxis_title="Fiscal year end", legend={"orientation": "h"})
    figure.update_yaxes(
        tickformat=".2f" if name in display.MULTIPLES else ",.0f" if name in display.DOLLARS else ".0%",
        title=(
            None if name not in display.DOLLARS
            else "millions, each in its own currency" if mixed
            else f"{display.symbol(next(iter(currencies.values())))}M"
        ),
    )
    st.plotly_chart(figure)


def run() -> None:
    st.set_page_config(page_title="Finance Analyzer", layout="wide")
    use_secret_user_agent()
    PAGES["company"] = st.Page(company_page, title="Company")
    PAGES["compare"] = st.Page(compare_page, title="Compare")
    page = st.navigation(list(PAGES.values()))
    open_from_link()
    page.run()


# Streamlit runs this file as __main__; importing it (as the tests do) only defines the pages.
if __name__ == "__main__":
    run()
