from datetime import date, datetime

import pytest

from finance_analyzer.metrics import FORMULA_TEXT, FORMULAS, PRICE_FORMULAS, company_metrics, price_metrics
from finance_analyzer.store import StoredLineItem

M = 1_000_000  # fixtures are in $M, stored values are in dollars


def rows_from(years: dict[date, dict[str, float]], derivations=None):
    derivations = derivations or {}
    return [
        StoredLineItem(
            "TEST", item, end, value if item == "diluted_eps" else value * M, "USD", "accn",
            derivations.get(item, ""), datetime(2026, 11, 10),
        )
        for end, items in years.items()
        for item, value in items.items()
    ]


# Copied from the database (store.get_company) for the years the tests need.
AAPL = {
    # Interest expense reported in FY2023 but not since, so FY2026 coverage gets a reason.
    date(2023, 9, 30): {"revenue": 383285, "diluted_eps": 6.13, "interest_expense": 3933},
    date(2024, 9, 28): {"revenue": 391035, "diluted_eps": 6.08},
    date(2025, 9, 27): {
        "revenue": 416161, "diluted_eps": 7.46, "total_assets": 359241, "shareholders_equity": 73733,
        "total_equity": 73733, "short_term_debt": 20329, "long_term_debt": 78328, "cash": 35934,
        "short_term_investments": 18763,
    },
    date(2026, 9, 26): {
        "revenue": 478834, "cost_of_revenue": 245232, "operating_income": 158063, "pretax_income": 159237,
        "income_tax": 27062, "net_income": 132175, "diluted_eps": 8.98, "cash": 36305,
        "short_term_investments": 20417, "inventory": 14541, "current_assets": 173857, "total_assets": 404548,
        "short_term_debt": 11903, "current_liabilities": 169915, "long_term_debt": 68208,
        "total_equity": 112093, "shareholders_equity": 112093, "operating_cash_flow": 145097,
        "capital_expenditure": 9041,
    },
}
KO = {
    date(2022, 12, 31): {"revenue": 43004, "diluted_eps": 2.19},
    date(2023, 12, 31): {"revenue": 45754, "diluted_eps": 2.47},
    date(2024, 12, 31): {
        "revenue": 47061, "diluted_eps": 2.46, "total_assets": 100549, "shareholders_equity": 24856,
        "total_equity": 26372, "short_term_debt": 2147, "long_term_debt": 42375, "cash": 10828,
        "short_term_investments": 3743,
    },
    date(2025, 12, 31): {
        "revenue": 47941, "cost_of_revenue": 18397, "operating_income": 13762, "interest_expense": 1654,
        "pretax_income": 15998, "income_tax": 2861, "net_income": 13107, "diluted_eps": 3.04, "cash": 10270,
        "short_term_investments": 5536, "inventory": 4425, "current_assets": 31044, "total_assets": 104816,
        "short_term_debt": 3373, "current_liabilities": 21281, "long_term_debt": 42119, "total_equity": 34275,
        "shareholders_equity": 32169, "operating_cash_flow": 7408, "capital_expenditure": 2112,
    },
}

# Hand-calculated from the numbers above (worked in the plan, e.g. AAPL ROIC =
# 158063 × (1 − 27062/159237) ÷ ((135482 + 117693) / 2)).
EXPECTED = {
    "AAPL": {
        "gross_margin": 0.4879, "operating_margin": 0.3301, "net_margin": 0.2760, "roe": 1.4226,
        "roa": 0.3461, "roic": 1.0364, "current_ratio": 1.0232, "quick_ratio": 0.9376,
        "debt_to_equity": 0.7147, "asset_turnover": 1.2538, "fcf_margin": 0.2841, "revenue_growth": 0.1506,
        "revenue_cagr_3y": 0.0770, "eps_growth": 0.2038, "eps_cagr_3y": 0.1357, "equity_multiplier": 4.1102,
        "dupont": 1.4226,
    },
    "KO": {
        "gross_margin": 0.6163, "operating_margin": 0.2871, "net_margin": 0.2734, "roe": 0.4597,
        "roa": 0.1276, "roic": 0.1879, "current_ratio": 1.4588, "quick_ratio": 1.2508,
        "debt_to_equity": 1.4142, "interest_coverage": 8.3204, "asset_turnover": 0.4669, "fcf_margin": 0.1105,
        "revenue_growth": 0.0187, "revenue_cagr_3y": 0.0369, "eps_growth": 0.2358, "eps_cagr_3y": 0.1155,
        "equity_multiplier": 3.6013, "dupont": 0.4597,
    },
}


@pytest.mark.parametrize("company, data, year", [("AAPL", AAPL, date(2026, 9, 26)), ("KO", KO, date(2025, 12, 31))])
def test_hand_calculated_values(company, data, year):
    metrics = company_metrics(rows_from(data))[year]
    for name, expected in EXPECTED[company].items():
        assert metrics[name].value == pytest.approx(expected, abs=0.0001), name
        assert metrics[name].reason == "", name


def test_free_cash_flow_in_dollars():
    assert company_metrics(rows_from(AAPL))[date(2026, 9, 26)]["free_cash_flow"].value == 136056 * M
    assert company_metrics(rows_from(KO))[date(2025, 12, 31)]["free_cash_flow"].value == 5296 * M


def test_apple_interest_coverage_has_a_reason():
    coverage = company_metrics(rows_from(AAPL))[date(2026, 9, 26)]["interest_coverage"]
    assert coverage.value is None
    assert coverage.reason == "interest_expense not reported for FY2026"


def test_dupont_factors_multiply_to_roe():
    metrics = company_metrics(rows_from(KO))[date(2025, 12, 31)]
    dupont = metrics["dupont"]
    factors = dupont.inputs["net margin"] * dupont.inputs["asset turnover"] * dupont.inputs["equity multiplier"]
    assert factors == pytest.approx(metrics["roe"].value)


def test_inputs_show_the_numbers_used():
    roe = company_metrics(rows_from(KO))[date(2025, 12, 31)]["roe"]
    assert roe.inputs == {
        "net_income": 13107 * M,
        "shareholders_equity": 32169 * M,
        "shareholders_equity (FY2024)": 24856 * M,
        "average shareholders_equity": (32169 + 24856) / 2 * M,
    }


def test_derivations_become_notes():
    rows = rows_from(KO, derivations={"short_term_debt": "short-term debt = commercial paper + other"})
    debt_to_equity = company_metrics(rows)[date(2025, 12, 31)]["debt_to_equity"]
    assert debt_to_equity.notes == ("short_term_debt: short-term debt = commercial paper + other",)


Y1, Y2, Y3 = date(2023, 12, 31), date(2024, 12, 31), date(2025, 12, 31)


def test_first_year_has_no_prior_year():
    metrics = company_metrics(rows_from({Y1: {"net_income": 10, "shareholders_equity": 100, "revenue": 50}}))[Y1]
    assert metrics["roe"].value is None and metrics["roe"].reason == "needs the prior fiscal year"
    assert metrics["revenue_growth"].reason == "needs the prior fiscal year"


def test_a_missing_year_breaks_the_chain():
    metrics = company_metrics(rows_from({Y1: {"revenue": 40}, Y3: {"revenue": 50}}))[Y3]
    assert metrics["revenue_growth"].reason == "needs the prior fiscal year"
    assert metrics["revenue_cagr_3y"].reason == "needs 3 consecutive prior years"


def test_never_reported_inventory_counts_as_zero_with_a_note():
    quick = company_metrics(rows_from({Y3: {"current_assets": 300, "current_liabilities": 100}}))[Y3]["quick_ratio"]
    assert quick.value == 3.0
    assert quick.notes == ("inventory assumed 0 (never reported)",)


def test_inventory_missing_in_one_year_is_not_zero():
    data = {Y2: {"inventory": 20}, Y3: {"current_assets": 300, "current_liabilities": 100}}
    quick = company_metrics(rows_from(data))[Y3]["quick_ratio"]
    assert quick.value is None and quick.reason == "inventory not reported for FY2025"


def test_negative_equity_has_a_reason():
    data = {Y2: {"shareholders_equity": -20}, Y3: {"net_income": 10, "shareholders_equity": -10}}
    roe = company_metrics(rows_from(data))[Y3]["roe"]
    assert roe.value is None and roe.reason == "average shareholders' equity is zero or negative"


def test_growth_from_a_loss_has_a_reason():
    data = {Y1: {"diluted_eps": 1.0}, Y2: {"diluted_eps": -0.5}, Y3: {"diluted_eps": 1.5}}
    growth = company_metrics(rows_from(data))[Y3]["eps_growth"]
    assert growth.value is None
    assert growth.reason == "prior-year diluted_eps is zero or negative, so growth isn't meaningful"


def test_zero_interest_expense_has_a_reason():
    data = {Y3: {"operating_income": 100, "interest_expense": 0}}
    coverage = company_metrics(rows_from(data))[Y3]["interest_coverage"]
    assert coverage.reason == "interest expense is zero or negative"


@pytest.mark.parametrize("income_tax, expected_note", [(-10, "tax rate of -10.0% is unusual"), (60, "tax rate of 60.0% is unusual")])
def test_unusual_tax_rate_still_calculates_roic_with_a_note(income_tax, expected_note):
    year = {"short_term_debt": 0, "long_term_debt": 0, "total_equity": 500, "cash": 0, "short_term_investments": 0}
    data = {Y2: year, Y3: {**year, "operating_income": 100, "pretax_income": 100, "income_tax": income_tax}}
    roic = company_metrics(rows_from(data))[Y3]["roic"]
    assert roic.value == pytest.approx(100 * (1 - income_tax / 100) / 500)
    assert roic.notes == (f"{expected_note}, so ROIC may be distorted",)


def test_every_year_gets_every_metric():
    metrics = company_metrics(rows_from(KO))
    assert all(len(year) == 19 for year in metrics.values())


def test_every_formula_has_text():
    assert FORMULA_TEXT.keys() == FORMULAS.keys() | PRICE_FORMULAS.keys()


def test_price_metrics_use_market_cap_and_the_latest_fiscal_year():
    """Hand-calculated from Apple FY2026 ($M) and a market cap of $3,700,000M."""
    result = price_metrics(rows_from(AAPL), 3_700_000 * M)
    assert result["market_cap"].value == 3_700_000 * M
    assert result["pe"].value == pytest.approx(3_700_000 / 132_175)  # 27.99
    assert result["pb"].value == pytest.approx(3_700_000 / 112_093)  # 33.01
    # EV = 3,700,000 + 11,903 + 68,208 − 36,305 − 20,417 = 3,723,389
    assert result["ev_ebit"].value == pytest.approx(3_723_389 / 158_063)  # 23.56
    assert result["ev_ebit"].inputs["enterprise value"] == 3_723_389 * M
    assert result["fcf_yield"].value == pytest.approx((145_097 - 9_041) / 3_700_000)  # 3.68%
    assert result["pe"].inputs == {"market cap": 3_700_000 * M, "net_income": 132_175 * M}


def test_price_metrics_are_all_unavailable_without_a_market_cap():
    result = price_metrics(rows_from(AAPL), None)
    assert result.keys() == PRICE_FORMULAS.keys()
    assert all(m.value is None and m.reason == "share price unavailable" for m in result.values())


def test_pe_is_unavailable_for_a_loss_but_fcf_yield_can_be_negative():
    year = {"net_income": -500, "operating_cash_flow": -100, "capital_expenditure": 50}
    result = price_metrics(rows_from({date(2026, 12, 31): year}), 10_000 * M)
    assert result["pe"].value is None and result["pe"].reason == "net income is zero or negative"
    assert result["fcf_yield"].value == pytest.approx(-0.015)


def test_valuation_ratios_convert_market_cap_into_the_currency_of_the_statements():
    """Apple's FY2026 figures read as TWD, a $100,000M market cap and 32 TWD to the dollar: TWD 3,200,000M."""
    rows = [row._replace(unit="TWD") for row in rows_from(AAPL)]
    result = price_metrics(rows, 100_000 * M, 32.0)
    assert result["market_cap"].value == 100_000 * M  # still in dollars
    assert result["market_cap"].inputs == {"market cap in US dollars": 100_000 * M}
    assert result["pe"].value == pytest.approx(3_200_000 / 132_175)
    assert result["pb"].value == pytest.approx(3_200_000 / 112_093)
    # EV = 3,200,000 + 11,903 + 68,208 − 36,305 − 20,417 = 3,223,389
    assert result["ev_ebit"].value == pytest.approx(3_223_389 / 158_063)
    assert result["fcf_yield"].value == pytest.approx((145_097 - 9_041) / 3_200_000)
    assert result["pe"].inputs == {
        "market cap in US dollars": 100_000 * M, "TWD per US dollar": 32.0,
        "market cap": 3_200_000 * M, "net_income": 132_175 * M,
    }


def test_valuation_ratios_are_unavailable_without_an_exchange_rate():
    rows = [row._replace(unit="EUR") for row in rows_from(AAPL)]
    result = price_metrics(rows, 3_700_000 * M)
    assert result["market_cap"].value == 3_700_000 * M
    for name in ("pe", "pb", "ev_ebit", "fcf_yield"):
        assert result[name].value is None and "no exchange rate from US dollars to EUR" in result[name].reason


def test_a_rate_is_ignored_when_the_statements_are_in_dollars():
    assert price_metrics(rows_from(AAPL), 3_700_000 * M, 32.0) == price_metrics(rows_from(AAPL), 3_700_000 * M)
