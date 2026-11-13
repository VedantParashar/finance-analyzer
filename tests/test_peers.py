import pytest

from finance_analyzer import peers

B = 1e9
COMPANIES = {
    "BIG": [3571, 400 * B], "MID": [3571, 100 * B], "SMALL": [3571, 20 * B], "TINY": [3571, 1 * B],
    "COUSIN": [3572, 90 * B], "COUSIN2": [3577, 5 * B], "OTHER": [2080, 100 * B],
}


@pytest.fixture(autouse=True)
def small_file(monkeypatch):
    monkeypatch.setattr(peers, "COMPANIES", COMPANIES)


def test_same_code_first_closest_revenue_first_then_the_three_digit_group():
    suggested = peers.suggest({"MID"}, 3571)
    # By ratio: 400 is 4× away, 20 is 5× away, 1 is 100× away. Then the 357x group: 90 before 5.
    assert [(p.ticker, p.same_code) for p in suggested] == [
        ("BIG", True), ("SMALL", True), ("TINY", True), ("COUSIN", False), ("COUSIN2", False)
    ]
    assert suggested[0].revenue == 400 * B


def test_limit_and_never_the_company_itself_or_another_industry():
    assert [p.ticker for p in peers.suggest({"MID"}, 3571, limit=2)] == ["BIG", "SMALL"]
    assert "OTHER" not in [p.ticker for p in peers.suggest({"MID"}, 3571, limit=99)]
    # Both share classes of one company are passed in, so neither is suggested to the other.
    assert [p.ticker for p in peers.suggest({"MID", "BIG"}, 3571, limit=2)] == ["SMALL", "TINY"]


def test_largest_first_when_the_companys_own_revenue_is_unknown():
    assert [p.ticker for p in peers.suggest({"FOREIGN"}, 3571)] == ["BIG", "MID", "SMALL", "TINY", "COUSIN"]


def test_no_suggestions_without_an_industry_code_or_without_company():
    assert peers.suggest({"MID"}, 0) == []
    assert peers.suggest({"OTHER"}, 2080) == []


def test_the_shipped_file_is_usable(monkeypatch):
    monkeypatch.undo()
    assert len(peers.COMPANIES) > 3000 and peers.REVENUE_YEAR >= 2025
    assert all(isinstance(code, int) and revenue > 0 for code, revenue in peers.COMPANIES.values())
    assert [p.ticker for p in peers.suggest({"KO"}, 2080)][0] == "PEP"
