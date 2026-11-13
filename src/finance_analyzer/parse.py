"""Turn SEC company facts into clean annual line items."""

import math
from collections import defaultdict
from collections.abc import Iterator
from datetime import date, timedelta
from typing import NamedTuple

from finance_analyzer.edgar import NoFinancialStatements, fetch_company_facts
from finance_analyzer.schema import (
    CASH_LAST_RESORT,
    CURRENT_BONDS,
    CURRENT_MATURITIES_OF_LONG_TERM_DEBT,
    IFRS_TAGS,
    ITEMS,
    LIABILITIES_AND_EQUITY,
    LONG_TERM_DEBT_LAST_RESORT,
    MARKETABLE_SECURITIES_ANY_TERM,
    OPERATING_EXPENSES,
    MARKETABLE_SECURITIES_NONCURRENT,
    MINORITY_INTEREST,
    NONCURRENT_BONDS,
    OTHER_SHORT_TERM_INVESTMENTS,
    SGA_PARTS,
    SHORT_TERM_BORROWING_PARTS,
    SHORT_TERM_BORROWINGS,
    TEMPORARY_EQUITY_PARTS,
    LineItem,
)

# Annual reports: 10-K for US companies, 20-F for most foreign ones, 40-F for Canadian ones; /A = amended.
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
QUARTERLY_FORMS = ANNUAL_FORMS | {"10-Q", "10-Q/A"}
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


def reporting_currency(facts: dict) -> str:
    """The currency of the statements, e.g. "USD" or "EUR": the one most annual total-assets facts are in.

    Foreign filers often add a US dollar translation of the latest year only, so "most" picks their own currency.
    """
    counts: dict[str, int] = defaultdict(int)
    for taxonomy in ("us-gaap", "ifrs-full"):
        for unit, values in facts.get("facts", {}).get(taxonomy, {}).get("Assets", {}).get("units", {}).items():
            counts[unit] += sum(fact["form"] in ANNUAL_FORMS for fact in values)
    return max(counts, key=counts.get) if any(counts.values()) else "USD"


def _taxonomy_by_year(facts: dict, currency: str) -> dict[str, str]:
    """Which taxonomy each year end's figures come from: that of the latest filing reporting its total assets.

    A company that changed from US GAAP to IFRS (Toyota, 2021) has some years under both. Mixing them within
    a year would, for example, add US GAAP temporary equity to an IFRS balance sheet that already counts it.
    """
    latest: dict[str, tuple[str, str]] = {}  # year end -> (filed, taxonomy)
    for taxonomy in ("us-gaap", "ifrs-full"):
        for fact in facts.get("facts", {}).get(taxonomy, {}).get("Assets", {}).get("units", {}).get(currency, []):
            if fact["form"] in ANNUAL_FORMS and (fact["end"] not in latest or fact["filed"] > latest[fact["end"]][0]):
                latest[fact["end"]] = (fact["filed"], taxonomy)
    return {end: taxonomy for end, (_, taxonomy) in latest.items()}


def company_currency(ticker: str) -> str:
    return reporting_currency(fetch_company_facts(ticker))


def _candidates(facts: dict, item: LineItem) -> Iterator[dict]:
    """Every annual-report fact for a line item in the reporting currency, in tag priority order."""
    if item.period_type == "flow":
        is_annual = _is_full_year
    else:
        year_ends = _fiscal_year_ends(facts)
        is_annual = lambda fact: "start" not in fact and fact["end"] in year_ends

    currency = reporting_currency(facts)
    unit = item.unit.replace("USD", currency)
    year_taxonomy = _taxonomy_by_year(facts, currency)
    for taxonomy, tags in (("us-gaap", item.tags), ("ifrs-full", IFRS_TAGS.get(item.name, ()))):
        for tag in tags:
            for fact in facts.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {}).get(unit, []):
                # Years with no balance sheet (the oldest income statements) take either taxonomy.
                if year_taxonomy.get(fact["end"], taxonomy) != taxonomy:
                    continue
                if fact["form"] in ANNUAL_FORMS and is_annual(fact):
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


def _splits(facts: dict, item: LineItem, quarterly: bool = False) -> dict[str, float]:
    """Stock splits seen in a per-share item, as {first filing on the new basis: factor}.

    With quarterly=True the quarterly reports are read too, which dates a split to the first 10-Q after it
    rather than the first annual report.
    """
    candidates = _period_candidates if quarterly else _candidates
    period = (lambda fact: (fact["end"], _period(fact))) if quarterly else (lambda fact: fact["end"])
    net_income: dict[tuple, int] = {}
    for fact in candidates(facts, ITEMS["net_income"]):
        net_income.setdefault((period(fact), fact["accn"]), fact["val"])

    by_period: dict = defaultdict(dict)  # period -> filed -> fact
    for fact in candidates(facts, item):
        by_period[period(fact)][fact["filed"]] = fact

    changes = []
    for filings in by_period.values():
        in_order = [filings[filed] for filed in sorted(filings)]
        changes += zip(in_order, in_order[1:])

    splits: dict[str, float] = {}
    # Largest values last: rounding distorts them least, so they decide the ratio.
    for older, newer in sorted(changes, key=lambda pair: abs(pair[0]["val"])):
        factor = _split_factor(older["val"], newer["val"])
        income_before = net_income.get((period(older), older["accn"]))
        income_after = net_income.get((period(newer), newer["accn"]))
        if factor is None or income_before is None or income_after is None:
            continue
        # A split changes per-share figures but not the company's profit.
        if abs(income_after - income_before) <= SPLIT_NET_INCOME_TOLERANCE * abs(income_before):
            splits[newer["filed"]] = factor
    if not quarterly:
        return splits
    # Each later report restates one more old period, so one split is sighted in several filings. Sightings
    # within about a year are the same split: dated by the first, sized by the largest figure (the last added).
    sightings: list[list[str]] = []
    for filed in sorted(splits):
        if sightings and (date.fromisoformat(filed) - date.fromisoformat(sightings[-1][0])).days <= 400:
            sightings[-1].append(filed)
        else:
            sightings.append([filed])
    by_size = list(splits)  # in the order added: smallest figure first
    return {group[0]: splits[max(group, key=by_size.index)] for group in sightings}


def annual_revenue(facts: dict) -> list[tuple[str, int, str]]:
    """Annual revenue as (fiscal_year_end, value, accn), oldest first."""
    return _annual_values(facts, ITEMS["revenue"])


def _temporary_equity_rows(facts: dict) -> list[LineItemRow]:
    """Temporary equity: the sum of its two parts, or the total tag when neither part is reported."""
    minority, parent = (
        {end: (value, accn) for end, value, accn in _annual_values(facts, part)} for part in TEMPORARY_EQUITY_PARTS
    )
    from_parts = minority.keys() | parent.keys()
    rows = [row for row in _item_rows(facts, ITEMS["temporary_equity"]) if row.fiscal_year_end not in from_parts]
    for end in from_parts:
        if end in minority and end in parent:
            value, accn = minority[end][0] + parent[end][0], minority[end][1]
            derivation = "temporary equity = redeemable minority interest + parent's temporary equity"
        else:
            (value, accn), derivation = minority.get(end) or parent[end], ""
        rows.append(LineItemRow("temporary_equity", end, value, accn, derivation))
    return rows


def _derived_liabilities(facts: dict) -> list[LineItemRow]:
    """Liabilities for year ends that report none: the balance sheet total minus everything else on that side."""
    reported = {end for end, _, _ in _annual_values(facts, ITEMS["total_liabilities"])}
    equity = {end: value for end, value, _ in _annual_values(facts, ITEMS["total_equity"])}
    temporary = {row.fiscal_year_end: row.value for row in _temporary_equity_rows(facts)}
    rows = []
    for end, total, accn in _annual_values(facts, LIABILITIES_AND_EQUITY):
        if end in reported or end not in equity:
            continue
        if temporary.get(end):
            value, derivation = total - equity[end] - temporary[end], "liabilities = total − equity − temporary equity"
        else:
            value, derivation = total - equity[end], "liabilities = total − equity"
        rows.append(LineItemRow("total_liabilities", end, value, accn, derivation))
    return rows


def _by_end(facts: dict, item: LineItem) -> dict[str, tuple[int | float, str]]:
    return {end: (value, accn) for end, value, accn in _annual_values(facts, item)}


def _with_separate_bonds(rows: list[LineItemRow], facts: dict, item: str, bonds: LineItem) -> list[LineItemRow]:
    """IFRS filers only: add bonds that a company reports apart from its borrowings (TSMC).

    Most companies' borrowings figure already includes their bonds (Novo Nordisk), and adding them again
    would count them twice. So bonds are added only when they're larger than the borrowings figure:
    a part can't be bigger than its whole.
    """
    by_end = {row.fiscal_year_end: row for row in rows}
    for end, (value, accn) in _by_end(facts, bonds).items():
        row = by_end.get(end)
        if row is None and value:
            by_end[end] = LineItemRow(item, end, value, accn, "bonds issued (no other borrowings reported)")
        elif row is not None and value > row.value:
            derivation = f"{row.derivation or 'borrowings'} + bonds issued, reported apart from borrowings"
            by_end[end] = row._replace(value=row.value + value, derivation=derivation)
    return list(by_end.values())


def _short_term_debt_rows(facts: dict) -> list[LineItemRow]:
    """DebtCurrent where reported, otherwise borrowings plus current maturities of long-term debt."""
    total = _by_end(facts, ITEMS["short_term_debt"])
    borrowings = _by_end(facts, SHORT_TERM_BORROWINGS)
    borrowing_parts = [(part.name, _by_end(facts, part)) for part in SHORT_TERM_BORROWING_PARTS]
    maturities = _by_end(facts, CURRENT_MATURITIES_OF_LONG_TERM_DEBT)

    rows = [LineItemRow("short_term_debt", end, value, accn, "") for end, (value, accn) in total.items()]
    ends = borrowings.keys() | maturities.keys() | {end for _, part in borrowing_parts for end in part}
    for end in ends - total.keys():
        if end in borrowings:
            parts = [(SHORT_TERM_BORROWINGS.name, borrowings[end])]
        else:
            parts = [(name, part[end]) for name, part in borrowing_parts if end in part]
        if end in maturities:
            parts.append((CURRENT_MATURITIES_OF_LONG_TERM_DEBT.name, maturities[end]))
        value = sum(value for _, (value, _) in parts)
        derivation = "short-term debt = " + " + ".join(name for name, _ in parts)
        rows.append(LineItemRow("short_term_debt", end, value, parts[0][1][1], derivation))
    return _with_separate_bonds(rows, facts, "short_term_debt", CURRENT_BONDS)


def _short_term_investments_rows(facts: dict) -> list[LineItemRow]:
    """Marketable securities plus other short-term investments, which can be separate balance sheet lines."""
    securities = _by_end(facts, ITEMS["short_term_investments"])
    any_term = _by_end(facts, MARKETABLE_SECURITIES_ANY_TERM)
    noncurrent = _by_end(facts, MARKETABLE_SECURITIES_NONCURRENT)
    investments = _by_end(facts, OTHER_SHORT_TERM_INVESTMENTS)

    rows = []
    for end in securities.keys() | any_term.keys() | investments.keys():
        marketable, derivation = securities.get(end), ""
        if marketable is None and end in any_term and end not in noncurrent:
            marketable, derivation = any_term[end], "MarketableSecurities assumed current"
        other = investments.get(end)
        if marketable is not None and other is not None and marketable[0] != other[0]:
            value, accn = marketable[0] + other[0], marketable[1]
            derivation = "short-term investments = marketable securities + short-term investments"
        elif marketable is not None or other is not None:
            # Equal values in both groups are one line tagged twice (Tesla FY2021), so count it once.
            value, accn = marketable if marketable is not None else other
        else:
            continue  # only MarketableSecurities, in a year it may include long-dated securities
        rows.append(LineItemRow("short_term_investments", end, value, accn, derivation))
    return rows


def _long_term_debt_rows(facts: dict) -> list[LineItemRow]:
    """Non-current debt, falling back to the ambiguous LongTermDebt tag only where nothing else exists."""
    rows = _item_rows(facts, ITEMS["long_term_debt"])
    covered = {row.fiscal_year_end for row in rows}
    rows += [
        LineItemRow("long_term_debt", end, value, accn, "LongTermDebt assumed non-current")
        for end, value, accn in _annual_values(facts, LONG_TERM_DEBT_LAST_RESORT)
        if end not in covered
    ]
    return _with_separate_bonds(rows, facts, "long_term_debt", NONCURRENT_BONDS)


def _cash_rows(facts: dict) -> list[LineItemRow]:
    """Cash and equivalents, falling back to the total that includes restricted cash where that's all there is."""
    rows = _item_rows(facts, ITEMS["cash"])
    covered = {row.fiscal_year_end for row in rows}
    rows += [
        LineItemRow("cash", end, value, accn, "includes restricted cash")
        for end, value, accn in _annual_values(facts, CASH_LAST_RESORT)
        if end not in covered
    ]
    return rows


def _shareholders_equity_rows(facts: dict) -> list[LineItemRow]:
    """The parent's owners' equity; where it isn't reported, total equity less any minority interest."""
    rows = _item_rows(facts, ITEMS["shareholders_equity"])
    covered = {row.fiscal_year_end for row in rows}
    minority = _by_end(facts, MINORITY_INTEREST)
    balance_sheet_years = _by_end(facts, ITEMS["total_assets"])
    for end, total, accn in _annual_values(facts, ITEMS["total_equity"]):
        # Only for years with a balance sheet: stray equity figures exist for older years (KO FY2007 shows 0).
        if end in covered or end not in balance_sheet_years:
            continue
        if end in minority:
            value, derivation = total - minority[end][0], "shareholders' equity = total equity − minority interest"
        else:
            value, derivation = total, "total equity (no minority interest reported)"
        rows.append(LineItemRow("shareholders_equity", end, value, accn, derivation))
    return rows


SCALE_SLIPS = (1_000, 1_000_000)  # thousands or millions typed as units: the usual XBRL scaling mistake


def _revenue_rows(facts: dict) -> list[LineItemRow]:
    """Revenue, but where another revenue tag gives the same year 1,000× or 1,000,000× smaller, the smaller one.

    A few filers tag one figure twice with the scale wrong on one of them (Tigo Energy, FY2025: $103.5M
    also filed as $103.5bn). A real business doesn't report two revenues a round thousand times apart.
    Same rule as scripts/build_peers.py.
    """
    others: dict[str, list[float]] = defaultdict(list)  # year end -> every revenue figure for that year
    for fact in _candidates(facts, ITEMS["revenue"]):
        if _is_full_year(fact):
            others[fact["end"]].append(fact["val"])
    rows = []
    for row in _item_rows(facts, ITEMS["revenue"]):
        smaller = next(
            (other for other in others[row.fiscal_year_end] for scale in SCALE_SLIPS
             if other > 0 and math.isclose(other * scale, row.value, rel_tol=0.001)),
            None,
        )
        if smaller is not None:
            times = f"{row.value / smaller:,.0f}"
            row = row._replace(value=smaller, derivation=f"revenue was also tagged {times}× larger; the smaller figure is used")
        rows.append(row)
    return rows


def _sga_rows(facts: dict) -> list[LineItemRow]:
    """The SG&A total where reported, otherwise selling/marketing plus administrative costs."""
    rows = _item_rows(facts, ITEMS["selling_general_admin"])
    covered = {row.fiscal_year_end for row in rows}
    parts = [(part.name, _by_end(facts, part)) for part in SGA_PARTS]
    for end in {end for _, by_end in parts for end in by_end} - covered:
        found = [(name, by_end[end]) for name, by_end in parts if end in by_end]
        value = sum(value for _, (value, _) in found)
        derivation = " + ".join(name for name, _ in found) + (" only" if len(found) == 1 else "")
        rows.append(LineItemRow("selling_general_admin", end, value, found[0][1][1], derivation))
    return rows


def _scale_text(multiplier: float) -> str:
    return f"split-adjusted ×{multiplier:g}" if multiplier > 1 else f"split-adjusted ÷{1 / multiplier:g}"


def _item_rows(facts: dict, item: LineItem) -> list[LineItemRow]:
    """A line item's rows, with per-share values and share counts rescaled to the latest share basis."""
    # Splits are detected from EPS; share counts move the opposite way to per-share values.
    splits = _splits(facts, ITEMS["diluted_eps"]) if item.unit in ("USD/shares", "shares") else {}
    rows = []
    for fact in _annual_facts(facts, item):
        # Only splits first seen in a later filing: this filing already reflects earlier ones.
        factor = math.prod(ratio for filed, ratio in splits.items() if filed > fact["filed"])
        value, derivation = fact["val"], ""
        if factor != 1 and item.unit == "shares":
            value, derivation = value * factor, _scale_text(factor)
        elif factor != 1:
            value, derivation = value / factor, _scale_text(1 / factor)
        rows.append(LineItemRow(item.name, fact["end"], value, fact["accn"], derivation))
    return rows


def _line_items(facts: dict, financial: bool = False) -> list[LineItemRow]:
    built_from_parts = {
        "temporary_equity": _temporary_equity_rows,
        "short_term_debt": _short_term_debt_rows,
        "short_term_investments": _short_term_investments_rows,
        "long_term_debt": _long_term_debt_rows,
        "cash": _cash_rows,
        "shareholders_equity": _shareholders_equity_rows,
        "selling_general_admin": _sga_rows,
        "revenue": _revenue_rows,
    }
    rows = [
        row
        for item in ITEMS.values()
        for row in (built_from_parts[item.name](facts) if item.name in built_from_parts else _item_rows(facts, item))
    ]
    rows += _derived_liabilities(facts)
    rows += _derived_operating_income(facts, rows, financial)
    order = list(ITEMS)
    return sorted(rows, key=lambda row: (order.index(row.item), row.fiscal_year_end))


def _derived_operating_income(facts: dict, rows: list[LineItemRow], financial: bool) -> list[LineItemRow]:
    """Operating income for years with no subtotal reported (#29); reported years are never touched.

    First choice: revenue − cost of revenue − operating expenses. Otherwise EBIT: pretax income + interest
    expense, a close cousin that also counts other income, and labelled so. Never EBIT for banks, brokers
    and insurers (financial=True): their interest is an operating cost, so adding it back means nothing.
    Not used: revenue − total costs and expenses (CostsAndExpenses). At Chevron that total holds every cost
    before tax, so the result equals pretax income; at Realty Income it includes interest; at Berkshire it
    doesn't match the revenue figure and gives −$71bn. Nor a sum of whichever cost lines happen to be
    tagged: those miss lines (Lilly's research costs) and overstate the result.
    """
    by_item = defaultdict(dict)
    for row in rows:
        by_item[row.item][row.fiscal_year_end] = row
    operating = _by_end(facts, OPERATING_EXPENSES)
    revenue, cost, pretax, interest = (by_item[name] for name in ("revenue", "cost_of_revenue", "pretax_income", "interest_expense"))
    derived = []
    for end in sorted(set(revenue) | set(pretax)):
        if end in by_item["operating_income"]:
            continue
        if end in revenue and end in cost and end in operating:
            value, accn = revenue[end].value - cost[end].value - operating[end][0], operating[end][1]
            derivation = ("operating income = revenue − cost of revenue − operating expenses (no operating income "
                          "subtotal reported)")
        elif end in pretax and end in interest and not financial:  # a missing interest figure isn't zero
            value, accn = pretax[end].value + interest[end].value, pretax[end].accn
            derivation = ("EBIT = pretax income + interest expense, used because no operating income subtotal is "
                          "reported; unlike operating income it also counts other income and losses")
        else:
            continue
        derived.append(LineItemRow("operating_income", end, value, accn, derivation))
    return derived


class NoAnnualReports(ValueError):
    """The company has financial data at the SEC, but none of it comes from an annual report we read."""


def annual_line_items(ticker: str, financial: bool = False) -> list[LineItemRow]:
    """Every standard line item for a ticker, by schema order then oldest year first.

    financial: the company is a bank, broker or insurer (see edgar.is_financial), which changes one derivation.
    """
    facts = fetch_company_facts(ticker)
    name = ticker.strip().upper()
    if not any(facts.get("facts", {}).get(taxonomy) for taxonomy in ("us-gaap", "ifrs-full")):
        raise NoFinancialStatements(
            f"{name} files with the SEC but reports no financial statements as data. "
            "It's probably an ETF or a fund, which this app can't analyse."
        )
    rows = _line_items(facts, financial)
    if not rows:
        raise NoAnnualReports(
            f"{name} has no annual report (10-K, 20-F or 40-F) in the SEC's data. That usually means a company "
            "that listed recently and hasn't filed its first one yet. For a few established companies "
            "(ExxonMobil is one) the SEC's data feed itself only carries quarterly figures."
        )
    return rows


def balance_checks(facts: dict) -> list[BalanceCheck]:
    """Check each year's balance sheet adds up, oldest year first.

    Reported liabilities: assets = liabilities + temporary equity + total equity.
    Derived liabilities make that true by construction, so those years are checked
    against the reported balance sheet total instead.
    """
    rows = _line_items(facts)

    def by_end(name: str) -> dict[str, LineItemRow]:
        return {row.fiscal_year_end: row for row in rows if row.item == name}

    assets, liabilities, equity = by_end("total_assets"), by_end("total_liabilities"), by_end("total_equity")
    temporary = {end: row.value for end, row in by_end("temporary_equity").items()}
    reported_total = {end: value for end, value, _ in _annual_values(facts, LIABILITIES_AND_EQUITY)}

    checks = []
    for end in sorted(assets.keys() & liabilities.keys() & equity.keys()):
        derived = bool(liabilities[end].derivation)
        reported_sum = liabilities[end].value + temporary.get(end, 0) + equity[end].value
        other_side = reported_total[end] if derived else reported_sum
        difference = assets[end].value - other_side
        passed = abs(difference) <= BALANCE_TOLERANCE * abs(assets[end].value)
        checks.append(BalanceCheck(end, passed, difference, derived))
    return checks


# ---- Quarters and the trailing twelve months (TTM) ----
#
# A 10-Q gives each flow item for the quarter and/or for the year so far (6 or 9 months); the fourth
# quarter is never reported on its own. So: Q4 = full year − first nine months, and TTM = the last four
# quarters. To reuse every rule above, the TTM figures are then written back as if they were annual
# facts for a "year" ending at the latest quarter, and run through _line_items unchanged.

# Days in a quarter, 6 months, 9 months and a year. The low ends allow for 12-week quarters (Costco).
_PERIODS = {"Q": (80, 100), "H": (160, 190), "N": (245, 285), "Y": (350, 380)}


class NoQuarterlyReports(ValueError):
    """The company's SEC data has no quarterly reports, so there is nothing more recent than its annual figures."""


def _period(fact: dict) -> str | None:
    days = (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days
    return next((name for name, (low, high) in _PERIODS.items() if low <= days <= high), None)


def _period_candidates(facts: dict, item: LineItem) -> Iterator[dict]:
    """Every quarterly- or annual-report fact for a flow item that covers a quarter, 6 or 9 months, or a year."""
    unit = item.unit.replace("USD", reporting_currency(facts))
    for taxonomy, tags in (("us-gaap", item.tags), ("ifrs-full", IFRS_TAGS.get(item.name, ()))):
        for tag in tags:
            for fact in facts.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {}).get(unit, []):
                if "start" in fact and fact["form"] in QUARTERLY_FORMS and _period(fact):
                    yield fact


def _quarters(tag_facts: list[dict]) -> dict[str, tuple[float, bool, dict]]:
    """One tag's value for each single quarter, by quarter end: (value, derived?, the fact it came from).

    Q1 is as reported; Q2 and Q3 are as reported, or the year-to-date figure minus the quarters before;
    Q4 is always the full year minus the first nine months.
    """
    latest: dict[tuple[str, str], dict] = {}  # (period end, period length) -> the most recently filed fact
    for fact in tag_facts:
        if "start" not in fact or fact["form"] not in QUARTERLY_FORMS or _period(fact) is None:
            continue
        if _period(fact) == "Y" and fact["form"] not in ANNUAL_FORMS:
            continue  # a rolling twelve months in a 10-Q (Amazon), not a fiscal year
        key = (fact["end"], _period(fact))
        if key not in latest or fact["filed"] > latest[key]["filed"]:
            latest[key] = fact

    year_ends = sorted(end for end, length in latest if length == "Y")
    quarters: dict[str, tuple[float, bool, dict]] = {}
    for index, year_end in enumerate([*year_ends, None]):  # None = the year still in progress
        if index == 0 and year_end is None:
            break  # no full year at all
        opened = date.fromisoformat(year_ends[index - 1]) if index else date.fromisoformat(year_end) - timedelta(371)
        closes = date.fromisoformat(year_end) if year_end else date.max
        so_far: dict[int, float] = {}  # quarter number -> total for the year up to that quarter
        for end in sorted({end for end, length in latest if length != "Y" and opened < date.fromisoformat(end) < closes}):
            number = round((date.fromisoformat(end) - opened).days / 91.31)
            alone, to_date = latest.get((end, "Q")), latest.get((end, {2: "H", 3: "N"}.get(number, "")))
            before = so_far.get(number - 1, 0 if number == 1 else None)
            if number not in (1, 2, 3) or (alone is None and (to_date is None or before is None)):
                continue
            if alone is not None:
                quarters[end] = (alone["val"], False, alone)
            else:
                quarters[end] = (to_date["val"] - before, True, to_date)
            if to_date is not None:
                so_far[number] = to_date["val"]
            elif before is not None:
                so_far[number] = before + alone["val"]
        if year_end and 3 in so_far:
            full_year = latest[(year_end, "Y")]
            quarters[year_end] = (full_year["val"] - so_far[3], True, full_year)
    return quarters


def _same_quarter_ends(facts: dict, currency: str) -> list[str]:
    """The latest balance sheet date, then the same quarter end in each earlier year; newest first."""
    ends = sorted({
        fact["end"]
        for taxonomy in ("us-gaap", "ifrs-full")
        for fact in facts.get("facts", {}).get(taxonomy, {}).get("Assets", {}).get("units", {}).get(currency, [])
        if fact["form"] in QUARTERLY_FORMS
    })
    chosen = ends[-1:]
    while chosen:
        target = date.fromisoformat(chosen[-1]) - timedelta(365)
        # 52/53-week calendars move the quarter end by a few days from year to year.
        near = [end for end in ends if abs((date.fromisoformat(end) - target).days) <= 10]
        if not near:
            break
        chosen.append(min(near, key=lambda end: abs((date.fromisoformat(end) - target).days)))
    return chosen


def _as_years_ending(facts: dict, ends: list[str]) -> dict:
    """The same facts restated as if each date in `ends` closed a fiscal year: flows become TTM figures."""
    splits = _splits(facts, ITEMS["diluted_eps"], quarterly=True)
    restated: dict = {"facts": {}}
    for taxonomy in ("us-gaap", "ifrs-full"):
        for tag, body in facts.get("facts", {}).get(taxonomy, {}).items():
            for unit, tag_facts in body.get("units", {}).items():
                per_share, count = unit.endswith("/shares"), unit == "shares"
                if per_share or count:  # put every figure on today's share basis before adding quarters up
                    tag_facts = [
                        {**fact, "val": fact["val"] * factor if count else fact["val"] / factor}
                        for fact in tag_facts
                        for factor in [math.prod(ratio for filed, ratio in splits.items() if filed > fact["filed"])]
                    ]
                new = [
                    {**fact, "form": "10-K"}
                    for fact in tag_facts
                    if "start" not in fact and fact["end"] in ends and fact["form"] in QUARTERLY_FORMS
                ]
                quarters = _quarters(tag_facts)
                quarter_ends = sorted(quarters)
                for end in ends:
                    if end not in quarters:
                        continue
                    last_four = quarter_ends[: quarter_ends.index(end) + 1][-4:]
                    span = (date.fromisoformat(end) - date.fromisoformat(last_four[0])).days
                    if len(last_four) < 4 or not 260 <= span <= 290:
                        continue  # a quarter is missing, so there's no honest twelve-month total
                    sources = [quarters[quarter][2] for quarter in last_four]
                    # A weighted-average share count can't be added up: use the one for the latest period reported.
                    value = sources[-1]["val"] if count else sum(quarters[quarter][0] for quarter in last_four)
                    new.append({
                        "start": (date.fromisoformat(end) - timedelta(364)).isoformat(), "end": end, "val": value,
                        "form": "10-K", "filed": max(source["filed"] for source in sources), "accn": sources[-1]["accn"],
                    })
                if new:
                    restated["facts"].setdefault(taxonomy, {}).setdefault(tag, {"units": {}})["units"][unit] = new
    return restated


def trailing_twelve_months(facts: dict, financial: bool = False) -> list[LineItemRow]:
    """Every line item for the twelve months to the latest quarter end, and to the same quarter in earlier years.

    Flow items are the sum of four quarters; balance sheet items are as reported on that date. Each row's
    fiscal_year_end is the quarter end, so the metrics engine treats the series like fiscal years.
    """
    currency = reporting_currency(facts)
    quarterly = any(
        fact["form"] not in ANNUAL_FORMS and fact["form"] in QUARTERLY_FORMS
        for taxonomy in ("us-gaap", "ifrs-full")
        for fact in facts.get("facts", {}).get(taxonomy, {}).get("Assets", {}).get("units", {}).get(currency, [])
    )
    ends = _same_quarter_ends(facts, currency)
    rows = _line_items(_as_years_ending(facts, ends), financial) if quarterly else []
    if not any(row.fiscal_year_end == ends[0] for row in rows):
        raise NoQuarterlyReports(
            "No usable quarterly figures in the SEC's data for this company. Companies that file a 20-F or "
            "40-F (most foreign ones) report to the SEC once a year, so only the annual view is available for them."
        )
    return rows


QUARTERLY_ITEMS = ("revenue", "cost_of_revenue", "operating_income", "net_income", "diluted_eps",
                   "operating_cash_flow", "capital_expenditure")


def quarterly_values(facts: dict, count: int = 8) -> dict[str, dict[str, tuple[float, bool]]]:
    """The main flow items for the last `count` single quarters: item -> quarter end -> (value, derived?)."""
    currency = reporting_currency(facts)
    result: dict[str, dict[str, tuple[float, bool]]] = {}
    for name in QUARTERLY_ITEMS:
        item, merged = ITEMS[name], {}
        for taxonomy, tags in (("us-gaap", item.tags), ("ifrs-full", IFRS_TAGS.get(name, ()))):
            for tag in tags:
                unit = item.unit.replace("USD", currency)
                tag_facts = facts.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {}).get(unit, [])
                for end, (value, derived, _) in _quarters(tag_facts).items():
                    merged.setdefault(end, (value, derived))  # the first tag in priority order wins
        result[name] = merged
    recent = sorted({end for values in result.values() for end in values})[-count:]
    return {name: {end: values[end] for end in recent if end in values} for name, values in result.items()}
