"""The four red-flag scores, checked against values worked out by hand from real filings."""

from datetime import date

import pytest

from finance_analyzer import display
from finance_analyzer.metrics import RED_FLAG_FORMULAS, company_metrics
from test_metrics import rows_from

# Copied from the database (store.get_company), in $M; diluted shares in millions.
AAPL = {
    date(2024, 9, 28): {
        "revenue": 391035, "cost_of_revenue": 210352, "net_income": 93736, "current_assets": 152987,
        "total_assets": 364980, "current_liabilities": 176392, "long_term_debt": 85750,
    },
    date(2025, 9, 27): {
        "revenue": 416161, "cost_of_revenue": 220960, "selling_general_admin": 27601, "net_income": 112010,
        "diluted_shares": 15004.697, "receivables": 39777, "current_assets": 147957,
        "property_plant_equipment": 49834, "total_assets": 359241, "current_liabilities": 165631,
        "long_term_debt": 78328, "operating_cash_flow": 111482, "depreciation_amortization": 11698,
    },
    date(2026, 9, 26): {
        "revenue": 478834, "cost_of_revenue": 245232, "selling_general_admin": 29774, "operating_income": 158063,
        "net_income": 132175, "diluted_shares": 14720.306, "receivables": 43817, "current_assets": 173857,
        "property_plant_equipment": 52084, "total_assets": 404548, "current_liabilities": 169915,
        "long_term_debt": 68208, "total_liabilities": 292455, "retained_earnings": 13700, "total_equity": 112093,
        "operating_cash_flow": 145097, "depreciation_amortization": 13423,
    },
}
KO = {
    date(2023, 12, 31): {
        "revenue": 45754, "cost_of_revenue": 18520, "net_income": 10714, "current_assets": 26732,
        "total_assets": 97703, "current_liabilities": 23571, "long_term_debt": 35547,
    },
    date(2024, 12, 31): {
        "revenue": 47061, "cost_of_revenue": 18324, "selling_general_admin": 14582, "net_income": 10631,
        "diluted_shares": 4320, "receivables": 3569, "current_assets": 25997, "property_plant_equipment": 10303,
        "total_assets": 100549, "current_liabilities": 25249, "long_term_debt": 42375,
        "operating_cash_flow": 6805, "depreciation_amortization": 1075,
    },
    date(2025, 12, 31): {
        "revenue": 47941, "cost_of_revenue": 18397, "selling_general_admin": 14521, "operating_income": 13762,
        "net_income": 13107, "diluted_shares": 4313, "receivables": 3038, "current_assets": 31044,
        "property_plant_equipment": 9613, "total_assets": 104816, "current_liabilities": 21281,
        "long_term_debt": 42119, "total_liabilities": 70541, "retained_earnings": 80382, "total_equity": 34275,
        "operating_cash_flow": 7408, "depreciation_amortization": 1050,
    },
}
LATEST = {"AAPL": (AAPL, date(2026, 9, 26)), "KO": (KO, date(2025, 12, 31))}


def scores(company):
    data, year = LATEST[company]
    return company_metrics(rows_from(data))[year]


# Altman Z″ = 6.56 × working capital/assets + 3.26 × retained earnings/assets + 6.72 × operating income/assets
#             + 1.05 × equity/liabilities
# AAPL: 6.56 × 3,942/404,548 + 3.26 × 13,700/404,548 + 6.72 × 158,063/404,548 + 1.05 × 112,093/292,455
#       = 0.0639 + 0.1104 + 2.6256 + 0.4024 = 3.2024
# KO:   6.56 × 9,763/104,816 + 3.26 × 80,382/104,816 + 6.72 × 13,762/104,816 + 1.05 × 34,275/70,541
#       = 0.6110 + 2.5001 + 0.8823 + 0.5102 = 4.5036
@pytest.mark.parametrize("company, expected", [("AAPL", 3.2024), ("KO", 4.5036)])
def test_altman_z_by_hand(company, expected):
    score = scores(company)["altman_z"]
    assert score.value == pytest.approx(expected, abs=0.0001) and score.reason == ""
    assert len([key for key in score.inputs if "÷" in key]) == 4  # the four ratios are shown


# Piotroski F: the nine tests, by hand.
# AAPL FY2026 passes all nine:
#   1 net income 132,175 > 0            2 cash flow 145,097 > 0
#   3 ROA 132,175/359,241 = 36.8% > 112,010/364,980 = 30.7%        4 cash flow 145,097 > profit 132,175
#   5 debt/avg assets 68,208/381,894.5 = 17.9% ≤ 78,328/362,110.5 = 21.6%
#   6 current ratio 1.023 > 0.893       7 shares 14,720 ≤ 15,005
#   8 gross margin 48.8% > 46.9%        9 turnover 478,834/359,241 = 1.333 > 416,161/364,980 = 1.140
# KO FY2025 fails two:
#   4 cash flow 7,408 < profit 13,107   9 turnover 47,941/100,549 = 0.4768 < 47,061/97,703 = 0.4817
#   (passes: 3 ROA 13.0% > 10.9%; 5 41.0% ≤ 42.7%; 6 1.459 > 1.030; 7 4,313 ≤ 4,320; 8 61.6% > 61.1%)
@pytest.mark.parametrize("company, expected, failed", [("AAPL", 9, []), ("KO", 7, [4, 9])])
def test_piotroski_f_by_hand(company, expected, failed):
    score = scores(company)["piotroski_f"]
    assert score.value == expected and score.reason == ""
    tests = {int(key.split(":")[0].removeprefix("test ")): value for key, value in score.inputs.items() if key.startswith("test ")}
    assert len(tests) == 9 and [number for number, passed in tests.items() if not passed] == failed


# Beneish M = −4.84 + 0.92 DSRI + 0.528 GMI + 0.404 AQI + 0.892 SGI + 0.115 DEPI − 0.172 SGAI + 4.679 TATA − 0.327 LVGI
# AAPL: DSRI (43,817/478,834) ÷ (39,777/416,161) = 0.9574     GMI 0.46905 ÷ 0.48786 = 0.9615
#       AQI (1 − 225,941/404,548) ÷ (1 − 197,791/359,241) = 0.9824     SGI 478,834/416,161 = 1.1506
#       DEPI (11,698/61,532) ÷ (13,423/65,507) = 0.9278       SGAI (29,774/478,834) ÷ (27,601/416,161) = 0.9375
#       TATA (132,175 − 145,097)/404,548 = −0.0319            LVGI (238,123/404,548) ÷ (243,959/359,241) = 0.8668
#       M = −2.5158
# KO:   DSRI 0.8356, GMI 0.9909, AQI 0.9579, SGI 1.0187, DEPI 0.9595, SGAI 0.9775, TATA 0.0544, LVGI 0.8994
#       M = −2.3499
BENEISH = {
    "AAPL": (-2.5158, [0.9574, 0.9615, 0.9824, 1.1506, 0.9278, 0.9375, -0.0319, 0.8668]),
    "KO": (-2.3499, [0.8356, 0.9909, 0.9579, 1.0187, 0.9595, 0.9775, 0.0544, 0.8994]),
}


@pytest.mark.parametrize("company", ["AAPL", "KO"])
def test_beneish_m_by_hand(company):
    expected, indexes = BENEISH[company]
    score = scores(company)["beneish_m"]
    assert score.value == pytest.approx(expected, abs=0.0001) and score.reason == ""
    names = ["receivables index", "gross margin index", "asset quality index", "sales growth index",
             "depreciation index", "SG&A index", "accruals to total assets", "leverage index"]
    assert [score.inputs[name] for name in names] == pytest.approx(indexes, abs=0.0001)


# Accruals ratio = (net income − operating cash flow) ÷ average total assets
# AAPL: (132,175 − 145,097) ÷ ((404,548 + 359,241)/2) = −12,922 ÷ 381,894.5 = −3.38%
# KO:   (13,107 − 7,408) ÷ ((104,816 + 100,549)/2) = 5,699 ÷ 102,682.5 = 5.55%
@pytest.mark.parametrize("company, expected", [("AAPL", -0.03384), ("KO", 0.05550)])
def test_accruals_ratio_by_hand(company, expected):
    assert scores(company)["accruals_ratio"].value == pytest.approx(expected, abs=0.00001)


def test_scores_are_calculated_for_every_year_and_say_why_when_they_cannot_be():
    metrics = company_metrics(rows_from(AAPL))
    assert all(RED_FLAG_FORMULAS.keys() <= year.keys() for year in metrics.values())
    middle = metrics[date(2025, 9, 27)]
    assert middle["piotroski_f"].reason == "needs 2 consecutive prior years"  # FY2023 isn't in the fixture
    assert middle["altman_z"].reason == "retained_earnings not reported for FY2025"
    assert middle["accruals_ratio"].value == pytest.approx((112010 - 111482) / ((359241 + 364980) / 2))


def test_a_bank_with_no_current_assets_gets_reasons_not_scores():
    year = {"total_assets": 4000, "net_income": 50, "operating_cash_flow": 40, "retained_earnings": 300}
    bank = company_metrics(rows_from({date(2024, 12, 31): year, date(2025, 12, 31): year}))[date(2025, 12, 31)]
    assert bank["altman_z"].reason == "current_assets not reported for FY2025"
    assert bank["beneish_m"].value is None and bank["piotroski_f"].value is None
    assert bank["accruals_ratio"].value == pytest.approx(10 / 4000)


def test_a_company_with_no_debt_passes_the_debt_test():
    data = {end: {k: v for k, v in items.items() if k != "long_term_debt"} for end, items in AAPL.items()}
    score = company_metrics(rows_from(data))[date(2026, 9, 26)]["piotroski_f"]
    assert score.value == 9 and "long_term_debt assumed 0 (never reported)" in score.notes


@pytest.mark.parametrize(
    "name, value, text, verdict",
    [
        ("altman_z", 3.2024, "3.20", "Safe zone (above 2.6)"),
        ("altman_z", 2.6, "2.60", "Grey zone (1.1 to 2.6)"),
        ("altman_z", 1.09, "1.09", "Distress zone (below 1.1)"),
        ("piotroski_f", 9.0, "9 of 9", "Strong (7 to 9)"),
        ("piotroski_f", 4.0, "4 of 9", "Average (4 to 6)"),
        ("piotroski_f", 3.0, "3 of 9", "Weak (0 to 3)"),
        ("beneish_m", -2.5158, "-2.52", "No flag (−1.78 or below)"),
        ("beneish_m", -1.15, "-1.15", "⚠ Flag: above −1.78"),
        ("accruals_ratio", -0.0338, "-3.4%", "No flag (10% or below)"),
        ("accruals_ratio", 0.11, "11.0%", "⚠ Flag: above 10%"),
    ],
)
def test_scores_are_formatted_and_judged_by_the_published_cut_offs(name, value, text, verdict):
    assert display.format_metric(name, value) == text and display.verdict(name, value) == verdict
