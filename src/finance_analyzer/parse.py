"""Turn SEC company facts into clean annual line items."""

from datetime import date

# In priority order: companies moved to the first tag with the ASC 606 revenue standard (2018).
REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]


def _annual_values(facts: dict, tags: list[str]) -> list[tuple[str, int, str]]:
    """Merge full-year 10-K values across tags, keeping the latest filing for each period."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    best: dict[tuple[str, str], dict] = {}  # (start, end) -> chosen fact
    for tag in tags:
        for fact in us_gaap.get(tag, {}).get("units", {}).get("USD", []):
            if fact["form"] != "10-K" or "start" not in fact:
                continue
            days = (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days
            if not 350 <= days <= 380:  # full years only; 52/53-week years are 364 or 371 days
                continue
            period = (fact["start"], fact["end"])
            # Strictly later only, so on a same-day tie the earlier tag in the list wins.
            if period not in best or fact["filed"] > best[period]["filed"]:
                best[period] = fact
    return sorted((f["end"], f["val"], f["accn"]) for f in best.values())


def annual_revenue(facts: dict) -> list[tuple[str, int, str]]:
    """Annual revenue as (fiscal_year_end, value, accn), oldest first."""
    return _annual_values(facts, REVENUE_TAGS)
