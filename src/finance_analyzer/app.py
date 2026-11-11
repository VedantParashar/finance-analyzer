"""The Streamlit UI. It only displays what the metrics engine computes.

Run from the project folder: uv run --env-file .env finance-analyzer
"""

from datetime import timedelta

import httpx
import plotly.graph_objects as go
import streamlit as st

from finance_analyzer import display, edgar, export, parse, prices, store
from finance_analyzer.metrics import FORMULA_TEXT, Metric, company_metrics, price_metrics

YEARS_SHOWN = 5
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


# Only successes are cached: an exception passes straight through, so the next page run tries again.
@st.cache_data(ttl=QUOTE_MINUTES * 60, show_spinner=False)
def quote(ticker: str) -> prices.Quote:
    return prices.fetch_quote(ticker)


def valuation(ticker: str, rows: list[store.StoredLineItem]) -> tuple[dict[str, Metric], str]:
    """The price-based metrics, and a sentence saying where the price came from or why there isn't one."""
    try:
        latest = quote(ticker)
    except prices.PriceUnavailable as error:
        return price_metrics(rows, None), f"Share price unavailable: {error}. The rest of the page doesn't need it."
    return price_metrics(rows, latest.market_cap), (
        f"Share price ${latest.price:,.2f} from Yahoo Finance, fetched {latest.fetched_at:%b %-d, %Y at %H:%M} UTC."
    )


def load_or_explain(ticker: str):
    """load(), or None after showing the user why it failed."""
    try:
        return load(ticker)
    except (ValueError, RuntimeError) as error:  # unknown ticker, nothing parseable, or no SEC_USER_AGENT
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


def metric_card(name: str, metric: Metric, prior: Metric | None) -> None:
    with st.container(border=True):
        st.metric(
            display.LABELS[name],
            display.format_metric(name, metric.value),
            delta=display.yoy_delta(name, metric.value, prior.value if prior else None),
            delta_color="inverse" if name == "debt_to_equity" else "normal",
        )
        if metric.reason:
            st.caption(f"Not available: {metric.reason}")
        for note in metric.notes:
            st.caption(f"ⓘ {note}")
        with st.expander("Formula and meaning"):
            st.markdown(f"**Formula:** {FORMULA_TEXT[name]}")
            for key, value in metric.inputs.items():
                st.markdown(f"- {key.replace('_', ' ')} = {display.format_input(key, value)}")
            if metric.value is not None:
                st.markdown(f"= **{display.format_metric(name, metric.value)}**")
            learn(name)


def learn(name: str) -> None:
    text = display.LEARNING[name]
    st.markdown(f"**What it means:** {text['meaning']}")
    st.markdown(f"**What's good:** {text['good']}")
    st.markdown(f"**Common traps:** {text['traps']}")


def trend_chart(title: str, labels: list[str], series: dict[str, list], kind: str, percent: bool) -> go.Figure:
    """Bars or lines over the years; None values show as gaps, never as zero."""
    trace = go.Bar if kind == "bar" else go.Scatter
    figure = go.Figure([trace(name=name, x=labels, y=values) for name, values in series.items()])
    figure.update_layout(title=title, height=320, margin={"t": 40, "b": 20}, legend={"orientation": "h"})
    figure.update_yaxes(tickformat=".0%" if percent else "$,.0f")
    return figure


def company_page() -> None:
    st.title("Company")
    ticker = st.text_input("Ticker", placeholder="e.g. AAPL").strip().upper()
    if not ticker:
        st.info("Enter a US stock ticker to see five years of statements and ratios from SEC filings.")
        return
    loaded = load_or_explain(ticker)
    if loaded is None:
        return
    rows, metrics, info = loaded

    st.header(f"{info['name']} ({ticker})")
    st.caption(info["industry"])
    bank_banner(ticker, info)
    st.download_button(
        "Download Excel with live formulas",
        export.company_workbook(ticker, rows, metrics),
        file_name=f"{ticker}_financials.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    refresh_button(ticker, rows)

    years = sorted(metrics)[-YEARS_SHOWN:]
    labels = [display.fiscal_year(end) for end in years]
    latest = metrics[years[-1]]
    prior = metrics[years[-2]] if len(years) > 1 else {}

    st.subheader("Line items")
    table, derivations = display.line_item_table(rows, years)
    st.dataframe(table, hide_index=True)
    if derivations:
        with st.expander("\\* Values we calculated rather than read straight from the filing"):
            st.markdown("\n".join(f"- {line}" for line in derivations))

    st.subheader(f"Metrics for {labels[-1]}")
    st.caption(f"Changes are against {labels[-2]}." if len(labels) > 1 else "No prior year stored.")
    for group, names in display.GROUPS.items():
        st.markdown(f"**{group}**")
        for column, name in zip(st.columns(4), names):
            with column:
                metric_card(name, latest[name], prior.get(name))

    st.subheader("Valuation at today's price")
    valuation_metrics, price_note = valuation(ticker, rows)
    st.caption(
        f"{price_note} Profit, equity, debt and cash flow are from {labels[-1]}, the last full fiscal year, so "
        "these differ from sites that use the last twelve months."
    )
    for column, name in zip(st.columns(5), display.PRICE_METRICS):
        with column:
            metric_card(name, valuation_metrics[name], None)

    st.subheader("Trends")
    by_key = {(row.item, row.fiscal_year_end): row.value / 1e6 for row in rows}
    left, right = st.columns(2)
    left.plotly_chart(
        trend_chart(
            "Revenue and net income ($M)",
            labels,
            {label: [by_key.get((item, end)) for end in years] for label, item in
             [("Revenue", "revenue"), ("Net income", "net_income")]},
            "bar",
            percent=False,
        )
    )
    right.plotly_chart(
        trend_chart(
            "Margins",
            labels,
            {display.LABELS[name]: [metrics[end][name].value for end in years] for name in display.GROUPS["Profitability"]},
            "line",
            percent=True,
        )
    )
    left.plotly_chart(
        trend_chart("Return on equity", labels, {"ROE": [metrics[end]["roe"].value for end in years]}, "line", True)
    )

    dupont_section(metrics, years, labels)
    data_checks_section(ticker, rows)


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
    tickers = display.parse_tickers(st.text_input("Tickers (2 to 4)", placeholder="e.g. AAPL, KO, NVDA"))
    if not 2 <= len(tickers) <= 4:
        st.info("Enter 2 to 4 tickers, separated by commas or spaces.")
        return
    companies = {}
    for ticker in tickers:
        loaded = load_or_explain(ticker)
        if loaded is None:
            return
        companies[ticker] = loaded
        bank_banner(ticker, loaded[2])

    latest_ends = {ticker: max(metrics) for ticker, (_, metrics, _) in companies.items()}
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
            line[columns[ticker]] = display.format_metric(name, metric.value)
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
    scale = 1e6 if name in display.DOLLARS else 1  # free cash flow in $M
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
        tickformat=".2f" if name in display.MULTIPLES else "$,.0f" if name in display.DOLLARS else ".0%",
        title="$M" if name in display.DOLLARS else None,
    )
    st.plotly_chart(figure)


# Streamlit runs this file as __main__; importing it (as the tests do) only defines the pages.
if __name__ == "__main__":
    st.set_page_config(page_title="Finance Analyzer", layout="wide")
    st.navigation([st.Page(company_page, title="Company"), st.Page(compare_page, title="Compare")]).run()
