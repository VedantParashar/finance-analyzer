import pytest

from finance_analyzer.parse import _annual_values, _line_items, annual_line_items, annual_revenue, balance_checks
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


def test_amended_10k_restatement_wins():
    facts = company(
        Assets=[
            instant("2018-09-29", 500, "2018-11-05", "ORIGINAL"),
            {**instant("2018-09-29", 510, "2019-01-25", "AMENDED"), "form": "10-K/A"},
        ]
    )
    assert _annual_values(facts, ITEMS["total_assets"]) == [("2018-09-29", 510, "AMENDED")]


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
        ("revenue", YEAR_END, 1, "R", ""),
        ("total_assets", YEAR_END, 500, "A", ""),
    ]


def test_liabilities_derived_when_not_reported(monkeypatch):
    facts = company(
        LiabilitiesAndStockholdersEquity=[instant(YEAR_END, 1000, FILED, "BS")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
    )
    derived = ("total_liabilities", YEAR_END, 700, "BS", "liabilities = total − equity")
    assert derived in line_items(monkeypatch, facts)


def test_reported_liabilities_are_not_replaced_by_derived(monkeypatch):
    facts = company(
        Liabilities=[instant(YEAR_END, 650, FILED, "L")],
        LiabilitiesAndStockholdersEquity=[instant(YEAR_END, 1000, FILED, "BS")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
    )
    rows = [row for row in line_items(monkeypatch, facts) if row.item == "total_liabilities"]
    assert rows == [("total_liabilities", YEAR_END, 650, "L", "")]


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


def test_balance_check_allows_a_small_difference_and_still_reports_it():
    def with_liabilities(liabilities):
        return company(
            Assets=[instant(YEAR_END, 100_000, FILED, "A")],
            Liabilities=[instant(YEAR_END, liabilities, FILED, "L")],
            StockholdersEquity=[instant(YEAR_END, 30_000, FILED, "EQ")],
        )

    assert balance_checks(with_liabilities(70_050)) == [(YEAR_END, True, -50, False)]  # 0.05%
    assert balance_checks(with_liabilities(70_150)) == [(YEAR_END, False, -150, False)]  # 0.15%


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


FY1, FY2, FY3, FY4 = "2016-12-31", "2017-12-31", "2018-12-31", "2019-12-31"
FILINGS = {"A": "2018-02-01", "B": "2019-02-01", "C": "2020-02-01"}


def annual(end, val, accn):
    start = f"{int(end[:4]) - 1}-12-31"
    return fact(start, end, val, "10-K", FILINGS[accn], accn)


def per_share_company(rows, income=lambda end, accn: 1000):
    """Company facts from (fiscal year end, EPS, filing) rows, with net income in the same filings."""
    return {
        "facts": {
            "us-gaap": {
                "EarningsPerShareDiluted": {"units": {"USD/shares": [annual(e, v, a) for e, v, a in rows]}},
                "NetIncomeLoss": {"units": {"USD": [annual(e, income(e, a), a) for e, _, a in rows]}},
            }
        }
    }


def eps_rows(facts):
    return [(r.fiscal_year_end, r.value, r.derivation) for r in _line_items(facts) if r.item == "diluted_eps"]


def one_change(old, new, older_year):
    """FY2's EPS changes from old to new in filing B; FY1 was last reported before that, in A."""
    return [(FY1, older_year, "A"), (FY2, old, "A"), (FY2, new, "B")]


@pytest.mark.parametrize(
    "old, new, older_year, rescaled, derivation",
    [
        (9.0, 4.5, 8.0, 4.0, "split-adjusted ÷2"),
        (44.15, 6.31, 27.68, 27.68 / 7, "split-adjusted ÷7"),
        (1.74, 0.17, 3.85, 0.385, "split-adjusted ÷10"),  # NVDA: rounded ratio is 10.24
        (9.0, 6.0, 3.0, 2.0, "split-adjusted ÷1.5"),  # 3-for-2
        (5.0, 4.0, 2.0, 1.6, "split-adjusted ÷1.25"),  # 5-for-4
        (-5.72, -1.14, -6.93, -6.93 / 5, "split-adjusted ÷5"),  # a loss per share still splits
        (0.5, 5.0, 0.3, 3.0, "split-adjusted ×10"),  # reverse split
    ],
)
def test_split_rescales_older_values(old, new, older_year, rescaled, derivation):
    rows = eps_rows(per_share_company(one_change(old, new, older_year)))
    assert rows == [(FY1, pytest.approx(rescaled), derivation), (FY2, new, "")]


@pytest.mark.parametrize(
    "old, new",
    [
        (5.36, 6.78),  # Apple's FY2008 restatement: not a split ratio
        (0.02, 0.01),  # looks like 2-for-1 but is one cent of rounding
        (0.05, 0.04),  # looks like 5-for-4 but is one cent of rounding
        (2.0, -1.0),  # sign change
    ],
)
def test_changes_that_are_not_splits_leave_values_alone(old, new):
    rows = eps_rows(per_share_company(one_change(old, new, 8.0)))
    assert rows == [(FY1, 8.0, ""), (FY2, new, "")]


def test_stacked_splits_multiply():
    facts = per_share_company(
        [(FY1, 8.0, "A"), (FY2, 9.0, "A"), (FY2, 4.5, "B"), (FY3, 5.0, "B"), (FY3, 1.25, "C"), (FY4, 1.5, "C")]
    )
    assert eps_rows(facts) == [
        (FY1, 1.0, "split-adjusted ÷8"),
        (FY2, 1.125, "split-adjusted ÷4"),
        (FY3, 1.25, ""),
        (FY4, 1.5, ""),
    ]


def test_split_ratio_rejected_when_net_income_moved():
    halved_profit = lambda end, accn: 500 if accn == "B" else 1000
    facts = per_share_company(one_change(9.0, 4.5, 8.0), income=halved_profit)
    assert eps_rows(facts) == [(FY1, 8.0, ""), (FY2, 4.5, "")]


def test_split_accepted_with_small_restatement():
    restated = lambda end, accn: 998 if accn == "B" else 1000  # KO's 2012 split moved income 0.2%
    facts = per_share_company(one_change(9.0, 4.5, 8.0), income=restated)
    assert eps_rows(facts) == [(FY1, 4.0, "split-adjusted ÷2"), (FY2, 4.5, "")]


def test_split_needs_net_income_to_confirm():
    facts = per_share_company(one_change(9.0, 4.5, 8.0))
    del facts["facts"]["us-gaap"]["NetIncomeLoss"]
    assert eps_rows(facts) == [(FY1, 8.0, ""), (FY2, 4.5, "")]


def test_splits_do_not_touch_dollar_items():
    facts = per_share_company(one_change(9.0, 4.5, 8.0))
    facts["facts"]["us-gaap"]["Revenues"] = {"units": {"USD": [annual(FY1, 800, "A"), annual(FY2, 900, "B")]}}
    revenue = [(r.value, r.derivation) for r in _line_items(facts) if r.item == "revenue"]
    assert revenue == [(800, ""), (900, "")]


SUM_OF_PARTS = "temporary equity = redeemable minority interest + parent's temporary equity"


def temporary_equity(facts):
    return [row for row in _line_items(facts) if row.item == "temporary_equity"]


def test_temporary_equity_adds_both_parts_and_balances():
    # Like Tesla FY2020: the "including" total tag leaves out the parent's part.
    facts = company(
        Assets=[instant(YEAR_END, 1000, FILED, "A")],
        Liabilities=[instant(YEAR_END, 600, FILED, "A")],
        StockholdersEquity=[instant(YEAR_END, 335, FILED, "A")],
        RedeemableNoncontrollingInterestEquityCarryingAmount=[instant(YEAR_END, 60, FILED, "A")],
        TemporaryEquityCarryingAmountAttributableToParent=[instant(YEAR_END, 5, FILED, "A")],
        TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests=[
            instant(YEAR_END, 60, FILED, "A")
        ],
    )
    assert temporary_equity(facts) == [("temporary_equity", YEAR_END, 65, "A", SUM_OF_PARTS)]
    assert balance_checks(facts) == [(YEAR_END, True, 0, False)]


def test_temporary_equity_from_one_part_is_as_reported():
    facts = company(TemporaryEquityValueExcludingAdditionalPaidInCapital=[instant(YEAR_END, 87, FILED, "N")])
    assert temporary_equity(facts) == [("temporary_equity", YEAR_END, 87, "N", "")]


def test_temporary_equity_total_tag_used_only_without_parts():
    facts = company(
        TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests=[
            instant(YEAR_END, 40, FILED, "T")
        ]
    )
    assert temporary_equity(facts) == [("temporary_equity", YEAR_END, 40, "T", "")]


def test_derived_liabilities_subtract_temporary_equity():
    facts = company(
        Assets=[instant(YEAR_END, 1000, FILED, "A")],
        LiabilitiesAndStockholdersEquity=[instant(YEAR_END, 1000, FILED, "BS")],
        StockholdersEquity=[instant(YEAR_END, 300, FILED, "EQ")],
        RedeemableNoncontrollingInterestEquityCarryingAmount=[instant(YEAR_END, 50, FILED, "BS")],
    )
    liabilities = [row for row in _line_items(facts) if row.item == "total_liabilities"]
    assert liabilities == [
        ("total_liabilities", YEAR_END, 650, "BS", "liabilities = total − equity − temporary equity")
    ]
    assert balance_checks(facts) == [(YEAR_END, True, 0, True)]


def test_unexplained_gap_still_fails():
    facts = company(
        Assets=[instant(YEAR_END, 1000, FILED, "A")],
        Liabilities=[instant(YEAR_END, 600, FILED, "A")],
        StockholdersEquity=[instant(YEAR_END, 335, FILED, "A")],
    )
    assert balance_checks(facts) == [(YEAR_END, False, 65, False)]


def rows_for(facts, name):
    return [(row.value, row.accn, row.derivation) for row in _line_items(facts) if row.item == name]


def test_short_term_debt_uses_reported_total():
    facts = company(
        DebtCurrent=[instant(YEAR_END, 999, FILED, "T")],
        LongTermDebtCurrent=[instant(YEAR_END, 999, FILED, "T")],
    )
    assert rows_for(facts, "short_term_debt") == [(999, "T", "")]


def test_short_term_debt_adds_parts_when_total_missing():
    # Like Apple: commercial paper plus the current part of long-term debt.
    facts = company(
        CommercialPaper=[instant(YEAR_END, 1997, FILED, "P")],
        OtherShortTermBorrowings=[instant(YEAR_END, 3, FILED, "P")],
        LongTermDebtCurrent=[instant(YEAR_END, 9906, FILED, "P")],
    )
    derivation = (
        "short-term debt = commercial paper + other short-term borrowings + current maturities of long-term debt"
    )
    assert rows_for(facts, "short_term_debt") == [(11906, "P", derivation)]


def test_short_term_borrowings_replace_their_parts():
    # Like KO 2022: ShortTermBorrowings (2,373) already equals commercial paper + other (2,146 + 227).
    facts = company(
        ShortTermBorrowings=[instant(YEAR_END, 2373, FILED, "K")],
        CommercialPaper=[instant(YEAR_END, 2146, FILED, "K")],
        OtherShortTermBorrowings=[instant(YEAR_END, 227, FILED, "K")],
        LongTermDebtAndCapitalLeaseObligationsCurrent=[instant(YEAR_END, 399, FILED, "K")],
    )
    derivation = "short-term debt = short-term borrowings + current maturities of long-term debt"
    assert rows_for(facts, "short_term_debt") == [(2772, "K", derivation)]


def test_long_term_debt_tag_is_a_labelled_last_resort():
    tesla_like = company(LongTermDebt=[instant(YEAR_END, 6584, FILED, "T")])
    assert rows_for(tesla_like, "long_term_debt") == [(6584, "T", "LongTermDebt assumed non-current")]

    apple_like = company(
        LongTermDebt=[instant(YEAR_END, 78114, FILED, "A")],  # total: would double count the current part
        LongTermDebtNoncurrent=[instant(YEAR_END, 68208, FILED, "A")],
    )
    assert rows_for(apple_like, "long_term_debt") == [(68208, "A", "")]


def test_share_counts_multiply_across_a_split():
    facts = per_share_company(one_change(9.0, 4.5, 8.0))  # a 2-for-1 seen in filing B
    shares = [annual(FY1, 100, "A"), annual(FY2, 220, "B")]
    facts["facts"]["us-gaap"]["WeightedAverageNumberOfDilutedSharesOutstanding"] = {"units": {"shares": shares}}
    assert rows_for(facts, "diluted_shares") == [(200, "A", "split-adjusted ×2"), (220, "B", "")]


def test_separate_investment_lines_are_added():
    # Like KO FY2025: "Marketable securities" and "Short-term investments" are two lines.
    facts = company(
        MarketableSecurities=[instant(YEAR_END, 1934, FILED, "K")],
        OtherShortTermInvestments=[instant(YEAR_END, 3602, FILED, "K")],
    )
    derivation = "short-term investments = marketable securities + short-term investments"
    assert rows_for(facts, "short_term_investments") == [(5536, "K", derivation)]


def test_one_investment_line_tagged_twice_counts_once():
    # Like Tesla FY2021: the same 131 under both tags.
    facts = company(
        MarketableSecuritiesCurrent=[instant(YEAR_END, 131, FILED, "T")],
        ShortTermInvestments=[instant(YEAR_END, 131, FILED, "T")],
    )
    assert rows_for(facts, "short_term_investments") == [(131, "T", "")]


def test_marketable_securities_fallback_is_labelled():
    facts = company(MarketableSecurities=[instant(YEAR_END, 2348, FILED, "K")])
    assert rows_for(facts, "short_term_investments") == [(2348, "K", "MarketableSecurities assumed current")]


def test_marketable_securities_fallback_skipped_when_long_dated_securities_exist():
    facts = company(
        MarketableSecurities=[instant(YEAR_END, 100, FILED, "A")],  # could be current + non-current
        MarketableSecuritiesNoncurrent=[instant(YEAR_END, 80, FILED, "A")],
    )
    assert rows_for(facts, "short_term_investments") == []


def test_single_investment_tag_is_as_reported():
    facts = company(ShortTermInvestments=[instant(YEAR_END, 27546, FILED, "T")])
    assert rows_for(facts, "short_term_investments") == [(27546, "T", "")]


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
