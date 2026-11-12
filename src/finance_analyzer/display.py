"""Turns engine results into text for the pages. No Streamlit here, so it's plain to test."""

import json
from datetime import date
from pathlib import Path

from finance_analyzer.parse import BALANCE_TOLERANCE, BalanceCheck
from finance_analyzer.schema import ITEMS
from finance_analyzer.store import StoredLineItem

LABELS = {
    "gross_margin": "Gross margin",
    "operating_margin": "Operating margin",
    "net_margin": "Net margin",
    "roe": "ROE",
    "roa": "ROA",
    "roic": "ROIC",
    "current_ratio": "Current ratio",
    "quick_ratio": "Quick ratio",
    "debt_to_equity": "Debt / equity",
    "interest_coverage": "Interest coverage",
    "asset_turnover": "Asset turnover",
    "equity_multiplier": "Equity multiplier",
    "free_cash_flow": "Free cash flow",
    "fcf_margin": "FCF margin",
    "revenue_growth": "Revenue growth",
    "revenue_cagr_3y": "Revenue CAGR (3y)",
    "eps_growth": "EPS growth",
    "eps_cagr_3y": "EPS CAGR (3y)",
    "dupont": "ROE (DuPont)",
    "market_cap": "Market cap",
    "pe": "P/E",
    "pb": "P/B",
    "ev_ebit": "EV / EBIT",
    "fcf_yield": "FCF yield",
}
PRICE_METRICS = ["market_cap", "pe", "pb", "ev_ebit", "fcf_yield"]  # need today's share price, see prices.py

# SPEC.md's metric groups; DuPont gets its own section on the page.
GROUPS = {
    "Profitability": ["gross_margin", "operating_margin", "net_margin"],
    "Returns": ["roe", "roa", "roic"],
    "Liquidity": ["current_ratio", "quick_ratio"],
    "Leverage": ["debt_to_equity", "interest_coverage", "equity_multiplier"],
    "Efficiency": ["asset_turnover"],
    "Cash flow": ["free_cash_flow", "fcf_margin"],
    "Growth": ["revenue_growth", "revenue_cagr_3y", "eps_growth", "eps_cagr_3y"],
}

# The learning layer: for each metric, what it means, what's good and common traps.
LEARNING: dict[str, dict[str, str]] = json.loads(Path(__file__).with_name("learning.json").read_text())

MULTIPLES = {
    "current_ratio", "quick_ratio", "debt_to_equity", "interest_coverage", "asset_turnover", "equity_multiplier",
    "pe", "pb", "ev_ebit",
}
DOLLARS = {"free_cash_flow", "market_cap"}  # every other metric is a fraction shown as a percentage


def fiscal_year(end: date) -> str:
    """FY label by the calendar year the fiscal year ends in, as the companies themselves do."""
    return f"FY{end.year}"


def currency(rows: list[StoredLineItem]) -> str:
    """The currency the company reports in, read from the stored units ("EUR", "EUR/shares")."""
    return next((row.unit.split("/")[0] for row in rows if row.unit != "shares"), "USD")


def symbol(currency: str) -> str:
    """What goes in front of an amount: "$" for dollars, otherwise the currency code and a space."""
    return "$" if currency == "USD" else f"{currency} "


def money(value: float, currency: str = "USD") -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol(currency)}{abs(value) / 1e6:,.0f}M"


def format_metric(name: str, value: float | None, currency: str = "USD") -> str:
    if value is None:
        return "unavailable" if name in PRICE_METRICS else "—"
    if name in MULTIPLES:
        return f"{value:.2f}×"
    if name == "market_cap":
        return money(value)  # from Yahoo Finance, always in dollars
    if name in DOLLARS:
        return money(value, currency)
    return f"{value:.1%}"


def yoy_delta(name: str, current: float | None, prior: float | None) -> str | None:
    """Change since the prior year: percentage points for ratios, × for multiples, % for dollars."""
    if current is None or prior is None:
        return None
    if name in MULTIPLES:
        return f"{current - prior:+.2f}×"
    if name in DOLLARS:
        return f"{(current - prior) / abs(prior):+.1%}" if prior else None
    return f"{(current - prior) * 100:+.1f} pp"


def format_value(unit: str, value: float) -> str:
    """A stored value with its unit: "EUR", "EUR/shares" or "shares"."""
    if unit.endswith("/shares"):
        return f"{symbol(unit.split('/')[0])}{value:,.2f}"
    if unit == "shares":
        return f"{value / 1e6:,.0f}M shares"
    return money(value, unit)


def format_input(key: str, value: float, currency: str = "USD") -> str:
    """Format one Metric.inputs entry, e.g. "average total_assets" or "cash (FY2024)"."""
    base = key.removeprefix("average ").split(" (FY")[0]
    if base in ITEMS:
        return format_value(ITEMS[base].unit.replace("USD", currency), value)
    if base == "market cap":
        return money(value)
    if "invested capital" in base or base == "enterprise value":
        return money(value, currency)
    if base in {"asset turnover", "equity multiplier"}:
        return f"{value:.2f}×"
    return f"{value:.1%}"  # tax rate, net margin


def label(item: str) -> str:
    return item.replace("_", " ").capitalize().replace("eps", "EPS")


def line_item_table(rows: list[StoredLineItem], years: list[date]) -> tuple[list[dict[str, str]], list[str]]:
    """One row per line item, one column per year; derived values end in " *".

    Also returns the derivations, one line each, for the footnote.
    """
    by_key = {(row.item, row.fiscal_year_end): row for row in rows}
    table, derivations = [], []
    for item in ITEMS:
        if not any((item, end) in by_key for end in years):
            continue
        line = {"Line item": label(item)}
        for end in years:
            row = by_key.get((item, end))
            if row is None:
                line[fiscal_year(end)] = "—"
                continue
            line[fiscal_year(end)] = format_value(row.unit, row.value) + (" *" if row.derivation else "")
            if row.derivation:
                derivations.append(f"{label(item)}, {fiscal_year(end)}: {row.derivation}")
        table.append(line)
    return table, derivations


def balance_check_table(rows: list[StoredLineItem], checks: list[BalanceCheck]) -> list[dict[str, str]]:
    """One row per stored fiscal year, newest first: did assets = liabilities + equity, and if not, why."""
    by_end = {date.fromisoformat(check.fiscal_year_end): check for check in checks}
    have = {(row.item, row.fiscal_year_end) for row in rows}
    table = []
    for end in sorted({row.fiscal_year_end for row in rows}, reverse=True):
        check = by_end.get(end)
        if check is None:
            absent = [i for i in ("total_assets", "total_liabilities", "total_equity") if (i, end) not in have]
            result, detail = "Not checked", f"{', '.join(absent)} not reported for this year"
        else:
            other_side = (
                "the reported total of liabilities and equity (liabilities aren't reported on their own)"
                if check.liabilities_derived
                else "liabilities + temporary equity + total equity"
            )
            if check.difference == 0:
                result, detail = "✓ Balances", f"total assets equal {other_side}"
            else:
                gap = money(abs(check.difference)) if abs(check.difference) >= 1e6 else "less than $1M"
                size = f"total assets are {gap} {'above' if check.difference > 0 else 'below'}"
                limit = f"the {BALANCE_TOLERANCE:.1%} of total assets allowed for rounding"
                if check.passed:
                    result, detail = "✓ Balances", f"{size} {other_side}, within {limit}"
                else:
                    result, detail = "✗ Doesn't balance", f"{size} {other_side}, more than {limit}"
        table.append({"Fiscal year": fiscal_year(end), "Assets = liabilities + equity": result, "Detail": detail})
    return table


def missing_years(year_ends: list[date]) -> list[str]:
    """One line for each gap between stored fiscal years (oldest first), with what it breaks."""
    lines = []
    for earlier, later in zip(year_ends, year_ends[1:]):
        if (later - earlier).days > 375:  # the same limit the metrics engine uses for "consecutive"
            lines.append(
                f"Nothing between {fiscal_year(earlier)} (ended {earlier:%b %-d, %Y}) and {fiscal_year(later)} "
                f"(ended {later:%b %-d, %Y}): the SEC data has no full-year 10-K figures for the time in "
                f"between, so growth and averaged ratios for {fiscal_year(later)} can't be calculated."
            )
    return lines


def year_end_note(latest_ends: dict[str, date]) -> str:
    """A warning when the companies' latest fiscal years end more than a month apart, else ""."""
    # Days, not months: 52/53-week years drift a few days, which doesn't change the period compared.
    if (max(latest_ends.values()) - min(latest_ends.values())).days <= 31:
        return ""
    ends = ", ".join(f"{ticker} {fiscal_year(end)} ends {end:%b %-d, %Y}" for ticker, end in latest_ends.items())
    return f"Fiscal years end on different dates ({ends}), so the latest years cover different months."
