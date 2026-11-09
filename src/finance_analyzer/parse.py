"""Turn SEC company facts into clean annual line items."""

import math
from collections import defaultdict
from collections.abc import Iterator
from datetime import date
from typing import NamedTuple

from finance_analyzer.edgar import fetch_company_facts
from finance_analyzer.schema import ITEMS, LIABILITIES_AND_EQUITY, LineItem

BALANCE_TOLERANCE = 0.001  # 0.1% of total assets, so small rounding differences still pass
SPLIT_NET_INCOME_TOLERANCE = 0.01  # 1%: real splits can arrive alongside small restatements


class LineItemRow(NamedTuple):
    item: str
    fiscal_year_end: str
    value: int | float
    accn: str
    derivation: str  # empty = as reported, otherwise how we calculated the value


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


def _candidates(facts: dict, item: LineItem) -> Iterator[dict]:
    """Every annual 10-K or 10-K/A fact for a line item, in tag priority order."""
    if item.period_type == "flow":
        is_annual = _is_full_year
    else:
        year_ends = _fiscal_year_ends(facts)
        is_annual = lambda fact: "start" not in fact and fact["end"] in year_ends

    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in item.tags:
        for fact in us_gaap.get(tag, {}).get("units", {}).get(item.unit, []):
            if fact["form"] in ("10-K", "10-K/A") and is_annual(fact):
                yield fact


def _annual_facts(facts: dict, item: LineItem) -> list[dict]:
    """The chosen fact for each year end, oldest first: latest filing, then tag order."""
    # Keyed by end only: filings sometimes disagree on a year's start date by a day.
    best: dict[str, dict] = {}  # fiscal year end -> chosen fact
    for fact in _candidates(facts, item):
        end = fact["end"]
        # Strictly later only, so on a same-day tie the earlier tag in the list wins.
        if end not in best or fact["filed"] > best[end]["filed"]:
            best[end] = fact
    return sorted(best.values(), key=lambda fact: fact["end"])


def _annual_values(facts: dict, item: LineItem) -> list[tuple[str, int | float, str]]:
    """Each year end's value exactly as reported, as (end, value, accn)."""
    return [(fact["end"], fact["val"], fact["accn"]) for fact in _annual_facts(facts, item)]


def _split_factor(old: float, new: float) -> float | None:
    """What to divide old-basis values by if this change looks like a split, else None."""
    # Opposite signs or zero can't be a split, and a one-cent change is only rounding.
    if old * new <= 0 or round(abs(old - new), 2) <= 0.01:
        return None
    larger, smaller = max(abs(old), abs(new)), min(abs(old), abs(new))
    for ratio in (1.25, 1.5, round(larger / smaller)):
        # Each per-share value is rounded to the cent, so allow half a cent on both.
        if ratio > 1 and abs(larger - smaller * ratio) <= 0.005 * (ratio + 1):
            return ratio if abs(old) > abs(new) else 1 / ratio  # below 1 = reverse split
    return None


def _splits(facts: dict, item: LineItem) -> dict[str, float]:
    """Stock splits seen in a per-share item, as {first filing on the new basis: factor}."""
    net_income: dict[tuple[str, str], int] = {}
    for fact in _candidates(facts, ITEMS["net_income"]):
        net_income.setdefault((fact["end"], fact["accn"]), fact["val"])

    by_period: dict[str, dict[str, dict]] = defaultdict(dict)  # end -> filed -> fact
    for fact in _candidates(facts, item):
        by_period[fact["end"]][fact["filed"]] = fact

    changes = []
    for filings in by_period.values():
        in_order = [filings[filed] for filed in sorted(filings)]
        changes += zip(in_order, in_order[1:])

    splits: dict[str, float] = {}
    # Largest values last: rounding distorts them least, so they decide the ratio.
    for older, newer in sorted(changes, key=lambda pair: abs(pair[0]["val"])):
        factor = _split_factor(older["val"], newer["val"])
        income_before = net_income.get((older["end"], older["accn"]))
        income_after = net_income.get((newer["end"], newer["accn"]))
        if factor is None or income_before is None or income_after is None:
            continue
        # A split changes per-share figures but not the company's profit.
        if abs(income_after - income_before) <= SPLIT_NET_INCOME_TOLERANCE * abs(income_before):
            splits[newer["filed"]] = factor
    return splits


def annual_revenue(facts: dict) -> list[tuple[str, int, str]]:
    """Annual revenue as (fiscal_year_end, value, accn), oldest first."""
    return _annual_values(facts, ITEMS["revenue"])


def _derived_liabilities(facts: dict) -> list[LineItemRow]:
    """Liabilities for year ends that report none: the balance sheet total minus total equity."""
    reported = {end for end, _, _ in _annual_values(facts, ITEMS["total_liabilities"])}
    equity = {end: value for end, value, _ in _annual_values(facts, ITEMS["total_equity"])}
    return [
        LineItemRow("total_liabilities", end, total - equity[end], accn, "liabilities = total − equity")
        for end, total, accn in _annual_values(facts, LIABILITIES_AND_EQUITY)
        if end not in reported and end in equity
    ]


def _item_rows(facts: dict, item: LineItem) -> list[LineItemRow]:
    """A line item's rows, with per-share values rescaled to the latest share basis."""
    splits = _splits(facts, item) if item.unit == "USD/shares" else {}
    rows = []
    for fact in _annual_facts(facts, item):
        # Only splits first seen in a later filing: this filing already reflects earlier ones.
        factor = math.prod(ratio for filed, ratio in splits.items() if filed > fact["filed"])
        value, derivation = fact["val"], ""
        if factor != 1:
            value /= factor
            derivation = f"split-adjusted ÷{factor:g}" if factor > 1 else f"split-adjusted ×{1 / factor:g}"
        rows.append(LineItemRow(item.name, fact["end"], value, fact["accn"], derivation))
    return rows


def _line_items(facts: dict) -> list[LineItemRow]:
    rows = [row for item in ITEMS.values() for row in _item_rows(facts, item)]
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
        derived = bool(liabilities[end].derivation)
        other_side = reported_total[end] if derived else liabilities[end].value + equity[end].value
        difference = assets[end].value - other_side
        passed = abs(difference) <= BALANCE_TOLERANCE * abs(assets[end].value)
        checks.append(BalanceCheck(end, passed, difference, derived))
    return checks
