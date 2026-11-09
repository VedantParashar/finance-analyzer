from finance_analyzer.parse import _annual_values, annual_line_items, annual_revenue, balance_checks
from finance_analyzer.schema import ITEMS

YEAR_END = "2018-09-29"
FILED = "2018-11-05"


def fact(start, end, val, form, filed, accn):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed, "accn": accn}


def instant(end, val, filed, accn):
    return {"end": end, "val": val, "form": "10-K", "filed": filed, "accn": accn}


def company(**tags):
    """Company facts with one list of USD facts per tag, plus a revenue flow ending 2018-09-29."""
    year = fact("2017-10-01", "2018-09-29", 1, "10-K", "2018-11-05", "R")
    us_gaap = {tag: {"units": {"USD": rows}} for tag, rows in tags.items()}
    us_gaap["Revenues"] = {"units": {"USD": [year]}}
    return {"facts": {"us-gaap": us_gaap}}


def test_instant_keeps_only_fiscal_year_ends():
    facts = company(
        Assets=[
            instant("2018-09-29", 500, "2018-11-05", "YEAR-END"),
            instant("2018-12-29", 999, "2019-11-05", "NOT-YEAR-END"),
        ]
    )
    assert _annual_values(facts, ITEMS["total_assets"]) == [("2018-09-29", 500, "YEAR-END")]


def test_instant_restatement_latest_filing_wins():
    facts = company(
        Assets=[
            instant("2018-09-29", 500, "2018-11-05", "OLD"),
            instant("2018-09-29", 510, "2019-10-31", "NEW"),
        ]
    )
    assert _annual_values(facts, ITEMS["total_assets"]) == [("2018-09-29", 510, "NEW")]


def test_flows_and_instants_do_not_mix():
    facts = company(
        # A period under an instant tag, and a snapshot under a flow tag: both ignored.
        Assets=[fact("2017-10-01", "2018-09-29", 500, "10-K", "2018-11-05", "A")],
        OperatingIncomeLoss=[instant("2018-09-29", 40, "2018-11-05", "B")],
    )
    assert _annual_values(facts, ITEMS["total_assets"]) == []
    assert _annual_values(facts, ITEMS["operating_income"]) == []


def test_eps_reads_the_per_share_unit():
    facts = company()
    facts["facts"]["us-gaap"]["EarningsPerShareDiluted"] = {
        "units": {
            "USD": [fact("2017-10-01", "2018-09-29", 999, "10-K", "2018-11-05", "WRONG")],
            "USD/shares": [fact("2017-10-01", "2018-09-29", 2.98, "10-K", "2018-11-05", "RIGHT")],
        }
    }
    assert _annual_values(facts, ITEMS["diluted_eps"]) == [("2018-09-29", 2.98, "RIGHT")]


def test_total_and_shareholders_equity_use_different_tags():
    facts = company(
        StockholdersEquity=[instant("2018-09-29", 90, "2018-11-05", "PARENT")],
        StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest=[
            instant("2018-09-29", 100, "2018-11-05", "TOTAL")
        ],
    )
    assert _annual_values(facts, ITEMS["total_equity"]) == [("2018-09-29", 100, "TOTAL")]
    assert _annual_values(facts, ITEMS["shareholders_equity"]) == [("2018-09-29", 90, "PARENT")]


def line_items(monkeypatch, facts):
    monkeypatch.setattr("finance_analyzer.parse.fetch_company_facts", lambda ticker: facts)
    return annual_line_items("TEST")


def test_annual_line_items_returns_rows_in_schema_order(monkeypatch):
    facts = company(Assets=[instant(YEAR_END, 500, FILED, "A")])
    assert line_items(monkeypatch, facts) == [
        ("revenue", YEAR_END, 1, "R", False),
        ("total_assets", YEAR_END, 500, "A", False),
    ]


def test_liabilities_derived_when_not_reported(monkeypatch):
    facts = company(
        LiabilitiesAndStockholdersEquity=[instant(YEAR_END, 1000, FILED, "BS")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
    )
    assert ("total_liabilities", YEAR_END, 700, "BS", True) in line_items(monkeypatch, facts)


def test_reported_liabilities_are_not_replaced_by_derived(monkeypatch):
    facts = company(
        Liabilities=[instant(YEAR_END, 650, FILED, "L")],
        LiabilitiesAndStockholdersEquity=[instant(YEAR_END, 1000, FILED, "BS")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
    )
    rows = [row for row in line_items(monkeypatch, facts) if row.item == "total_liabilities"]
    assert rows == [("total_liabilities", YEAR_END, 650, "L", False)]


def test_no_derived_liabilities_without_equity(monkeypatch):
    facts = company(LiabilitiesAndStockholdersEquity=[instant(YEAR_END, 1000, FILED, "BS")])
    assert not [row for row in line_items(monkeypatch, facts) if row.item == "total_liabilities"]


def test_balance_check_with_reported_liabilities():
    balanced = company(
        Assets=[instant(YEAR_END, 1000, FILED, "A")],
        Liabilities=[instant(YEAR_END, 700, FILED, "L")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
    )
    assert balance_checks(balanced) == [(YEAR_END, True, 0, False)]

    off_by_50 = company(
        Assets=[instant(YEAR_END, 1000, FILED, "A")],
        Liabilities=[instant(YEAR_END, 650, FILED, "L")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
    )
    assert balance_checks(off_by_50) == [(YEAR_END, False, 50, False)]


def test_balance_check_with_derived_liabilities_uses_reported_total():
    balanced = company(
        Assets=[instant(YEAR_END, 1000, FILED, "A")],
        LiabilitiesAndStockholdersEquity=[instant(YEAR_END, 1000, FILED, "BS")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
    )
    assert balance_checks(balanced) == [(YEAR_END, True, 0, True)]

    # Would pass if the derived value were fed back into assets = liabilities + equity.
    mismatch = company(
        Assets=[instant(YEAR_END, 1000, FILED, "A")],
        LiabilitiesAndStockholdersEquity=[instant(YEAR_END, 900, FILED, "BS")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
    )
    assert balance_checks(mismatch) == [(YEAR_END, False, 100, True)]


def test_revenue_falls_back_to_goods_tag():
    facts = {
        "facts": {
            "us-gaap": {
                "SalesRevenueGoodsNet": {
                    "units": {"USD": [fact("2017-10-01", YEAR_END, 7, "10-K", FILED, "G")]}
                }
            }
        }
    }
    assert annual_revenue(facts) == [(YEAR_END, 7, "G")]


def test_instants_need_a_flow_to_define_year_ends():
    facts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [instant("2018-09-29", 5, "2018-11-05", "A")]}}}}}
    assert _annual_values(facts, ITEMS["total_assets"]) == []


FAKE_FACTS = {
    "facts": {
        "us-gaap": {
            "SalesRevenueNet": {
                "units": {
                    "USD": [
                        # Older year, only under the old tag.
                        fact("2016-09-25", "2017-09-30", 100, "10-K", "2017-11-03", "A-2017"),
                        # Press release with a full-year period: not a 10-K, so dropped.
                        fact("2016-09-25", "2017-09-30", 999, "8-K", "2017-11-02", "A-8K"),
                    ]
                }
            },
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        # Duplicate year: the later filing (restated value) must win.
                        fact("2017-10-01", "2018-09-29", 200, "10-K", "2018-11-05", "A-2018"),
                        fact("2017-10-01", "2018-09-29", 210, "10-K", "2019-10-31", "A-2019"),
                        # Quarter (~90 days) and 6-month year-to-date: not full years, dropped.
                        fact("2018-09-30", "2018-12-29", 50, "10-Q", "2019-01-30", "A-Q1"),
                        fact("2018-09-30", "2019-03-30", 110, "10-Q", "2019-05-01", "A-H1"),
                    ]
                }
            },
        }
    }
}


def test_annual_revenue_merges_tags_and_filters():
    assert annual_revenue(FAKE_FACTS) == [
        ("2017-09-30", 100, "A-2017"),
        ("2018-09-29", 210, "A-2019"),
    ]


def test_same_day_tie_goes_to_earlier_tag():
    tie = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [fact("2017-10-01", "2018-09-29", 1, "10-K", "2018-11-05", "B")]}},
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [fact("2017-10-01", "2018-09-29", 2, "10-K", "2018-11-05", "A")]}
                },
            }
        }
    }
    assert annual_revenue(tie) == [("2018-09-29", 2, "A")]


def test_start_dates_one_day_apart_count_as_one_year():
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            fact("2017-09-30", "2018-09-29", 200, "10-K", "2018-11-05", "OLD"),
                            fact("2017-10-01", "2018-09-29", 210, "10-K", "2019-10-31", "NEW"),
                        ]
                    }
                }
            }
        }
    }
    assert annual_revenue(facts) == [("2018-09-29", 210, "NEW")]


def test_missing_tags_give_empty_list():
    assert annual_revenue({"facts": {"us-gaap": {}}}) == []
