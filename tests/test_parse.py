from finance_analyzer.parse import annual_revenue


def fact(start, end, val, form, filed, accn):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed, "accn": accn}


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
