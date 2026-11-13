"""Single quarters and the trailing twelve months, from hand-made filings."""

import pytest

from finance_analyzer import parse


def flow(start, end, val, form="10-Q", filed=None, accn="A"):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed or end, "accn": accn}


def point(end, val, form="10-Q"):
    return {"end": end, "val": val, "form": form, "filed": end, "accn": "A"}


# Calendar fiscal years. 2024: quarters of 10, 20, 30, 40 = 100. 2025: 15, 25, then 35 so far.
REVENUE = [
    flow("2024-01-01", "2024-03-31", 10),                       # Q1 on its own
    flow("2024-01-01", "2024-06-30", 30),                       # Q2 only as six months so far
    flow("2024-07-01", "2024-09-30", 30),                       # Q3 on its own...
    flow("2024-01-01", "2024-09-30", 60),                       # ...and as nine months so far
    flow("2024-01-01", "2024-12-31", 100, form="10-K"),
    flow("2025-01-01", "2025-03-31", 15),
    flow("2025-04-01", "2025-06-30", 25),
    flow("2025-01-01", "2025-06-30", 40),
    flow("2025-07-01", "2025-09-30", 35),
    flow("2025-01-01", "2025-09-30", 75),
]
ASSETS = [point("2024-09-30", 900), point("2024-12-31", 950, "10-K"), point("2025-09-30", 1000)]


def company(**tags):
    usd = {"Revenues": REVENUE, "Assets": ASSETS, **tags}
    return {"facts": {"us-gaap": {tag: {"units": {"USD": facts}} for tag, facts in usd.items()}}}


def test_quarters_are_as_reported_or_worked_out_from_the_year_so_far():
    quarters = {end: (value, derived) for end, (value, derived, _) in parse._quarters(REVENUE).items()}
    assert quarters == {
        "2024-03-31": (10, False),
        "2024-06-30": (20, True),   # 30 for six months − 10
        "2024-09-30": (30, False),
        "2024-12-31": (40, True),   # Q4 = 100 for the year − 60 for nine months
        "2025-03-31": (15, False),
        "2025-06-30": (25, False),
        "2025-09-30": (35, False),
    }


def test_trailing_twelve_months_adds_four_quarters_and_takes_the_balance_sheet_at_the_quarter_end():
    rows = {(row.item, row.fiscal_year_end): row.value for row in parse.trailing_twelve_months(company())}
    # Q4 2024 + Q1–Q3 2025 = 40 + 15 + 25 + 35; total assets as reported on Sep 30, not at the year end.
    assert rows[("revenue", "2025-09-30")] == 115
    assert rows[("total_assets", "2025-09-30")] == 1000
    # A year earlier only three quarters exist (2023 was never filed), so that period is left out entirely.
    assert {end for _, end in rows} == {"2025-09-30"}


def test_a_weighted_average_share_count_is_the_latest_quarters_not_a_sum():
    shares = [flow(f.get("start"), f["end"], 50 if f["end"] < "2025" else 48, f["form"]) for f in REVENUE]
    facts = company()
    facts["facts"]["us-gaap"]["WeightedAverageNumberOfDilutedSharesOutstanding"] = {"units": {"shares": shares}}
    rows = {(row.item, row.fiscal_year_end): row.value for row in parse.trailing_twelve_months(facts)}
    assert rows[("diluted_shares", "2025-09-30")] == 48


def test_a_missing_quarter_means_no_twelve_month_figure_rather_than_a_wrong_one():
    without_q1 = [f for f in REVENUE if f["end"] != "2025-03-31"]
    rows = parse.trailing_twelve_months(company(Revenues=without_q1, NetIncomeLoss=REVENUE))
    assert {row.item for row in rows} == {"net_income", "total_assets"}


def test_when_the_annual_report_is_the_latest_the_twelve_months_are_the_fiscal_year():
    up_to_year_end = company(Revenues=REVENUE[:5], Assets=ASSETS[:2])
    rows = {(row.item, row.fiscal_year_end): row.value for row in parse.trailing_twelve_months(up_to_year_end)}
    assert rows[("revenue", "2024-12-31")] == 100 and rows[("total_assets", "2024-12-31")] == 950


def test_a_company_with_only_annual_reports_has_no_quarterly_view():
    annual_only = company(Revenues=[REVENUE[4]], Assets=[ASSETS[1]])
    with pytest.raises(parse.NoQuarterlyReports, match="No usable quarterly figures"):
        parse.trailing_twelve_months(annual_only)


def test_quarterly_values_lists_recent_quarters_for_the_main_items():
    values = parse.quarterly_values(company(), count=3)
    assert values["revenue"] == {"2025-03-31": (15, False), "2025-06-30": (25, False), "2025-09-30": (35, False)}
    assert values["net_income"] == {}


def test_a_rolling_twelve_months_in_a_quarterly_report_is_not_a_fiscal_year():
    """Amazon's 10-Q also gives the twelve months to each quarter end; only annual reports mark year ends."""
    rolling = flow("2024-10-01", "2025-09-30", 115)  # in a 10-Q
    quarters = parse._quarters(REVENUE + [rolling])
    assert quarters["2025-09-30"][:2] == (35, False) and quarters["2024-12-31"][:2] == (40, True)


def test_twelve_week_quarters_are_recognised():
    """Costco's year: three 12-week quarters, then 16 weeks. Cash flow comes only for the year so far."""
    facts = [
        flow("2024-09-02", "2024-11-24", 10),
        flow("2024-09-02", "2025-02-16", 22),               # 24 weeks so far
        flow("2024-09-02", "2025-05-11", 36),               # 36 weeks so far
        flow("2024-09-02", "2025-08-31", 56, form="10-K"),  # 52 weeks
    ]
    assert {end: value for end, (value, _, _) in parse._quarters(facts).items()} == {
        "2024-11-24": 10, "2025-02-16": 12, "2025-05-11": 14, "2025-08-31": 20,
    }


def test_a_split_seen_in_several_later_reports_is_counted_once_and_figures_share_one_basis():
    """A 4-for-1 split in mid-2025: each later report restates one more old quarter on the new basis."""
    def per_share(old_basis):
        return [
            flow("2025-01-01", "2025-03-31", old_basis[0], filed="2025-04-20", accn="Q1"),
            flow("2025-04-01", "2025-06-30", old_basis[1] / 4, filed="2025-07-20", accn="Q2"),   # first report after the split
            flow("2025-01-01", "2025-06-30", (old_basis[0] + old_basis[1]) / 4, filed="2025-07-20", accn="Q2"),
            flow("2024-04-01", "2024-06-30", 2.0, filed="2024-07-20", accn="Q2-24"),
            flow("2024-04-01", "2024-06-30", 0.5, filed="2025-07-20", accn="Q2"),                # restated: first sighting
            flow("2024-07-01", "2024-09-30", 2.4, filed="2024-10-20", accn="Q3-24"),
            flow("2024-07-01", "2024-09-30", 0.6, filed="2025-10-20", accn="Q3"),                # restated: second sighting
            flow("2025-01-01", "2025-03-31", old_basis[0] / 4, filed="2026-04-20", accn="Q1-26"),
        ]

    income = [{**f, "val": 100} for f in per_share([4.0, 4.4])]
    facts = {"facts": {"us-gaap": {
        "EarningsPerShareDiluted": {"units": {"USD/shares": per_share([4.0, 4.4])}},
        "NetIncomeLoss": {"units": {"USD": income}},
        "Assets": {"units": {"USD": [point("2025-06-30", 1000)]}},
    }}}
    assert parse._splits(facts, parse.ITEMS["diluted_eps"], quarterly=True) == {"2025-07-20": 4}
