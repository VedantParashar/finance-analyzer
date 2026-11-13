from datetime import date, datetime

import pytest

from finance_analyzer import display
from finance_analyzer.metrics import FORMULAS, PRICE_FORMULAS, RED_FLAG_FORMULAS, REIT_FORMULAS
from finance_analyzer.parse import BalanceCheck
from finance_analyzer.store import StoredLineItem


def test_every_metric_has_a_label_and_every_grouped_metric_exists():
    assert display.LABELS.keys() == FORMULAS.keys() | RED_FLAG_FORMULAS.keys() | PRICE_FORMULAS.keys() | REIT_FORMULAS.keys()
    assert set(display.REIT_METRICS) == REIT_FORMULAS.keys()
    assert set(display.RED_FLAGS) == RED_FLAG_FORMULAS.keys()
    assert set(display.PRICE_METRICS) == PRICE_FORMULAS.keys()
    grouped = [name for names in display.GROUPS.values() for name in names]
    assert len(grouped) == len(set(grouped)) and set(grouped) == FORMULAS.keys() - {"dupont"}


@pytest.mark.parametrize(
    "name, value, expected",
    [
        ("net_margin", 0.27604, "27.6%"),
        ("current_ratio", 1.02316, "1.02×"),
        ("free_cash_flow", 136_056_000_000, "$136,056M"),
        ("free_cash_flow", -2_500_000, "-$2M"),
        ("roe", None, "—"),
        ("pe", 27.993, "27.99×"),
        ("pe", None, "unavailable"),
    ],
)
def test_format_metric(name, value, expected):
    assert display.format_metric(name, value) == expected


@pytest.mark.parametrize(
    "name, current, prior, expected",
    [
        ("net_margin", 0.276, 0.250, "+2.6 pp"),
        ("current_ratio", 1.0, 1.25, "-0.25×"),
        ("free_cash_flow", 110, 100, "+10.0%"),
        ("free_cash_flow", 110, 0, None),
        ("roe", 0.5, None, None),
    ],
)
def test_yoy_delta(name, current, prior, expected):
    assert display.yoy_delta(name, current, prior) == expected


@pytest.mark.parametrize(
    "key, value, expected",
    [
        ("net_income", 13_107_000_000, "$13,107M"),
        ("average shareholders_equity", 28_512_500_000, "$28,512M"),
        ("diluted_eps (FY2023)", 6.13, "$6.13"),
        ("diluted_shares", 15_408_095_000, "15,408M shares"),
        ("invested capital (prior year)", 117_693_000_000, "$117,693M"),
        ("tax rate", 0.17, "17.0%"),
        ("asset turnover", 1.2538, "1.25×"),
    ],
)
def test_format_input(key, value, expected):
    assert display.format_input(key, value) == expected


def row(item, end, value, unit="USD", derivation=""):
    return StoredLineItem("TEST", item, end, value, unit, "accn", derivation, datetime(2026, 11, 11))


def test_line_item_table_marks_derived_values_and_gaps():
    y1, y2 = date(2024, 12, 31), date(2025, 12, 31)
    rows = [
        row("revenue", y1, 100e6),
        row("revenue", y2, 120e6),
        row("diluted_eps", y2, 3.04, "USD/shares"),
        row("total_liabilities", y2, 70e6, derivation="liabilities = total − equity"),
        row("cash", date(2020, 12, 31), 5e6),  # outside the years shown
        row("net_income", y2, -1_234e6),
    ]
    table, derivations = display.line_item_table(rows, [y1, y2])
    assert table[:3] == [
        {"Line item": "Revenue", "FY2024": "100", "FY2025": "120"},
        {"Line item": "Net income", "FY2024": "—", "FY2025": "(1,234)"},  # negative: in parentheses
        {"Line item": "Diluted EPS (per share)", "FY2024": "—", "FY2025": "3.04"},
    ]
    assert table[3] == {"Line item": "Total liabilities", "FY2024": "—", "FY2025": "70 *"}
    assert derivations == ["Total liabilities, FY2025: liabilities = total − equity"]


def test_year_end_note_ignores_52_53_week_drift():
    assert display.year_end_note({"AAPL": date(2026, 9, 26), "MSFT": date(2026, 9, 30)}) == ""
    assert display.year_end_note({"KO": date(2025, 12, 31), "NVDA": date(2026, 1, 25)}) == ""


def test_year_end_note_names_each_year_end():
    note = display.year_end_note({"AAPL": date(2026, 9, 26), "KO": date(2025, 12, 31)})
    assert note == (
        "Fiscal years end on different dates (AAPL FY2026 ends Sep 26, 2026, KO FY2025 ends Dec 31, 2025), "
        "so the latest years cover different months."
    )


def test_every_metric_has_learning_text():
    assert display.LEARNING.keys() == FORMULAS.keys() | RED_FLAG_FORMULAS.keys() | PRICE_FORMULAS.keys() | REIT_FORMULAS.keys()
    for name, text in display.LEARNING.items():
        assert text.keys() == {"meaning", "good", "traps"}, name
        assert all(value.strip() for value in text.values()), name


def balance_rows(*ends, items=("total_assets", "total_liabilities", "total_equity")):
    return [StoredLineItem("T", item, end, 100e9, "USD", "accn", "", datetime(2026, 11, 10)) for end in ends for item in items]


def test_balance_check_table_explains_each_result():
    y23, y24, y25, y26 = (date(year, 12, 31) for year in (2023, 2024, 2025, 2026))
    rows = balance_rows(y24, y25, y26) + balance_rows(y23, items=("total_assets",))
    checks = [
        BalanceCheck("2024-12-31", False, -150e6, False),
        BalanceCheck("2025-12-31", True, 400_000, True),
        BalanceCheck("2026-12-31", True, 0, False),
    ]
    table = display.balance_check_table(rows, checks)
    assert [line["Fiscal year"] for line in table] == ["FY2026", "FY2025", "FY2024", "FY2023"]  # newest first
    assert [line["Assets = liabilities + equity"] for line in table] == [
        "✓ Balances", "✓ Balances", "✗ Doesn't balance", "Not checked",
    ]
    details = [line["Detail"] for line in table]
    assert details[0] == "total assets equal liabilities + temporary equity + total equity"
    assert details[1].startswith("total assets are less than $1M above the reported total of liabilities and equity")
    assert details[1].endswith("within the 0.1% of total assets allowed for rounding")
    assert details[2].startswith("total assets are $150M below liabilities") and "more than the 0.1%" in details[2]
    assert details[3] == "total_liabilities, total_equity not reported for this year"


def test_missing_years_reports_gaps_but_not_53_week_years():
    weekly = [date(2023, 9, 30), date(2024, 9, 28), date(2025, 9, 27)]  # 364-day years
    assert display.missing_years(weekly) == []
    assert display.missing_years([date(2020, 12, 31), date(2021, 12, 31), date(2023, 12, 31)]) == [
        "Nothing between FY2021 (ended Dec 31, 2021) and FY2023 (ended Dec 31, 2023): the SEC data has no "
        "full-year 10-K figures for the time in between, so growth and averaged ratios for FY2023 can't be calculated."
    ]


def test_amounts_carry_the_reporting_currency():
    assert display.money(1_500_000_000, "EUR") == "EUR 1,500M" and display.money(-2e6) == "-$2M"
    assert display.format_value("JPY/shares", 3052.5) == "JPY 3,052.50"
    assert display.format_value("USD/shares", 6.13) == "$6.13"
    assert display.format_metric("free_cash_flow", 5e9, "TWD") == "TWD 5,000M"
    assert display.format_metric("market_cap", 5e9, "TWD") == "$5,000M"  # Yahoo's market cap is in dollars
    assert display.format_input("revenue (FY2024)", 4e9, "EUR") == "EUR 4,000M"
    rows = [StoredLineItem("SAP", "diluted_eps", date(2025, 12, 31), 2.5, "EUR/shares", "a", "", datetime(2026, 1, 1))]
    assert display.currency(rows) == "EUR" and display.currency([]) == "USD"


def test_best_worst_follows_each_metrics_direction_and_skips_what_cant_be_ranked():
    assert display.best_worst("net_margin", {"AAPL": 0.27, "KO": 0.23, "NVDA": 0.55}) == ("NVDA", "KO")
    assert display.best_worst("debt_to_equity", {"AAPL": 1.5, "KO": 1.6, "NVDA": 0.1}) == ("NVDA", "KO")
    # A negative P/E means a loss, not a bargain: left out of the ranking.
    assert display.best_worst("pe", {"A": 30.0, "B": -5.0, "C": 12.0}) == ("C", "A")
    assert display.best_worst("altman_z", {"A": 3.2, "B": 4.5}) == (None, None)  # red flags keep their verdicts
    assert display.best_worst("roe", {"A": 0.1, "B": None}) == (None, None)  # one value: nothing to compare
    assert display.best_worst("roe", {"A": 0.1, "B": 0.1}) == (None, None)  # a tie
    assert display.best_worst("market_cap", {"A": 1e12, "B": 2e12}) == (None, None)  # size, not quality
    every_metric = [name for group in display.GROUPS.values() for name in group] + display.RED_FLAGS + display.PRICE_METRICS
    assert set(every_metric) - display.HIGHER_IS_BETTER - display.LOWER_IS_BETTER == {"equity_multiplier", "market_cap", *display.RED_FLAGS}


def test_source_column_links_the_latest_year_that_has_the_item():
    y1, y2 = date(2024, 12, 31), date(2025, 12, 31)
    rows = [
        StoredLineItem("TEST", "revenue", y1, 100e6, "USD", "OLD", "", datetime(2026, 11, 11)),
        StoredLineItem("TEST", "revenue", y2, 120e6, "USD", "NEW", "", datetime(2026, 11, 11)),
        StoredLineItem("TEST", "cash", y1, 5e6, "USD", "OLD", "", datetime(2026, 11, 11)),  # not reported in y2
    ]
    table, _ = display.line_item_table(rows, [y1, y2], sources={"OLD": "old-link", "NEW": "new-link"})
    assert [(line["Line item"], line["Source"]) for line in table] == [("Revenue", "new-link"), ("Cash", "old-link")]


def test_report_url_opens_a_prefilled_github_issue():
    from urllib.parse import parse_qs, urlparse

    url = display.report_url("AAPL", "ROE", "142.3%", "FY2026")
    assert url.startswith("https://github.com/VedantParashar/finance-analyzer/issues/new?")
    query = parse_qs(urlparse(url).query)
    assert query["title"] == ["Wrong number? AAPL ROE FY2026"] and query["labels"] == ["data-quality"]
    assert "**The app shows:** 142.3%" in query["body"][0]
