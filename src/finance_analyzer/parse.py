"""Turn SEC company facts into clean annual line items."""

from datetime import date
from typing import NamedTuple

from finance_analyzer.edgar import fetch_company_facts
from finance_analyzer.schema import ITEMS, LIABILITIES_AND_EQUITY, LineItem


class LineItemRow(NamedTuple):
    item: str
    fiscal_year_end: str
    value: int | float
    accn: str
    derived: bool  # True when we calculated the value instead of reading it from a filing


class BalanceCheck(NamedTuple):
    fiscal_year_end: str
    passed: bool
    difference: int
    liabilities_derived: bool


def _is_full_year(fact: dict) -> bool:
    if "start" not in fact:
        return False
    days = (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days
    return 350 <= days <= 380  # 52/53-week years are 364 or 371 days


def _fiscal_year_ends(facts: dict) -> set[str]:
    """Every date a full-year flow ended, which is how instants recognise a year-end."""
    return {
        end
        for item in ITEMS.values()
        if item.period_type == "flow"
        for end, _, _ in _annual_values(facts, item)
    }


def _annual_values(facts: dict, item: LineItem) -> list[tuple[str, int | float, str]]:
    """Merge a line item's 10-K values across tags, keeping the latest filing for each year end."""
    if item.period_type == "flow":
        is_annual = _is_full_year
    else:
        year_ends = _fiscal_year_ends(facts)
        is_annual = lambda fact: "start" not in fact and fact["end"] in year_ends

    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    # Keyed by end only: filings sometimes disagree on a year's start date by a day.
    best: dict[str, dict] = {}  # fiscal year end -> chosen fact
    for tag in item.tags:
        for fact in us_gaap.get(tag, {}).get("units", {}).get(item.unit, []):
            if fact["form"] not in ("10-K", "10-K/A") or not is_annual(fact):
                continue
            end = fact["end"]
            # Strictly later only, so on a same-day tie the earlier tag in the list wins.
            if end not in best or fact["filed"] > best[end]["filed"]:
                best[end] = fact
    return sorted((f["end"], f["val"], f["accn"]) for f in best.values())


def annual_revenue(facts: dict) -> list[tuple[str, int, str]]:
    """Annual revenue as (fiscal_year_end, value, accn), oldest first."""
    return _annual_values(facts, ITEMS["revenue"])


def _derived_liabilities(facts: dict) -> list[LineItemRow]:
    """Liabilities for year ends that report none: the balance sheet total minus total equity."""
    reported = {end for end, _, _ in _annual_values(facts, ITEMS["total_liabilities"])}
    equity = {end: value for end, value, _ in _annual_values(facts, ITEMS["total_equity"])}
    return [
        LineItemRow("total_liabilities", end, total - equity[end], accn, True)
        for end, total, accn in _annual_values(facts, LIABILITIES_AND_EQUITY)
        if end not in reported and end in equity
    ]


def _line_items(facts: dict) -> list[LineItemRow]:
    rows = [
        LineItemRow(item.name, end, value, accn, False)
        for item in ITEMS.values()
        for end, value, accn in _annual_values(facts, item)
    ]
    rows += _derived_liabilities(facts)
    order = list(ITEMS)
    return sorted(rows, key=lambda row: (order.index(row.item), row.fiscal_year_end))


def annual_line_items(ticker: str) -> list[LineItemRow]:
    """Every standard line item for a ticker, by schema order then oldest year first."""
    return _line_items(fetch_company_facts(ticker))


def balance_checks(facts: dict) -> list[BalanceCheck]:
    """Check each year's balance sheet adds up, oldest year first.

    Derived liabilities make assets = liabilities + equity true by construction,
    so those years are checked against the reported balance sheet total instead.
    """
    rows = _line_items(facts)

    def by_end(name: str) -> dict[str, LineItemRow]:
        return {row.fiscal_year_end: row for row in rows if row.item == name}

    assets, liabilities, equity = by_end("total_assets"), by_end("total_liabilities"), by_end("total_equity")
    reported_total = {end: value for end, value, _ in _annual_values(facts, LIABILITIES_AND_EQUITY)}

    checks = []
    for end in sorted(assets.keys() & liabilities.keys() & equity.keys()):
        derived = liabilities[end].derived
        other_side = reported_total[end] if derived else liabilities[end].value + equity[end].value
        difference = assets[end].value - other_side
        # shortcut: exact match only, add a tolerance if rounding causes false failures
        checks.append(BalanceCheck(end, difference == 0, difference, derived))
    return checks
