"""Turns engine results into text for the pages. No Streamlit here, so it's plain to test."""

import json
from datetime import date
from pathlib import Path

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
}

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

MULTIPLES = {"current_ratio", "quick_ratio", "debt_to_equity", "interest_coverage", "asset_turnover", "equity_multiplier"}
DOLLARS = {"free_cash_flow"}  # every other metric is a fraction shown as a percentage


def fiscal_year(end: date) -> str:
    """FY label by the calendar year the fiscal year ends in, as the companies themselves do."""
    return f"FY{end.year}"


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value) / 1e6:,.0f}M"


def format_metric(name: str, value: float | None) -> str:
    if value is None:
        return "—"
    if name in MULTIPLES:
        return f"{value:.2f}×"
    if name in DOLLARS:
        return money(value)
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
    if unit == "USD/shares":
        return f"${value:.2f}"
    if unit == "shares":
        return f"{value / 1e6:,.0f}M shares"
    return money(value)


def format_input(key: str, value: float) -> str:
    """Format one Metric.inputs entry, e.g. "average total_assets" or "cash (FY2024)"."""
    base = key.removeprefix("average ").split(" (FY")[0]
    if base in ITEMS:
        return format_value(ITEMS[base].unit, value)
    if "invested capital" in base:
        return money(value)
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


def parse_tickers(text: str) -> list[str]:
    """Tickers from free text like "aapl, KO nvda", uppercased, duplicates dropped, order kept."""
    return list(dict.fromkeys(text.replace(",", " ").upper().split()))


def year_end_note(latest_ends: dict[str, date]) -> str:
    """A warning when the companies' latest fiscal years end more than a month apart, else ""."""
    # Days, not months: 52/53-week years drift a few days, which doesn't change the period compared.
    if (max(latest_ends.values()) - min(latest_ends.values())).days <= 31:
        return ""
    ends = ", ".join(f"{ticker} {fiscal_year(end)} ends {end:%b %-d, %Y}" for ticker, end in latest_ends.items())
    return f"Fiscal years end on different dates ({ends}), so the latest years cover different months."
