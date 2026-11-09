from datetime import date

import pytest

from finance_analyzer import store
from finance_analyzer.parse import LineItemRow

YEAR_END = "2018-09-29"
ROWS = [
    LineItemRow("total_liabilities", YEAR_END, 700, "B", "liabilities = total − equity"),
    LineItemRow("revenue", YEAR_END, 100, "A", ""),
    LineItemRow("diluted_eps", YEAR_END, 2.98, "A", ""),
]


@pytest.fixture(autouse=True)
def temporary_database(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "new_folder" / "test.duckdb")


def parser_returns(monkeypatch, rows):
    monkeypatch.setattr(store, "annual_line_items", lambda ticker: rows)


def test_round_trip_keeps_every_field_in_schema_order(monkeypatch):
    parser_returns(monkeypatch, ROWS)
    assert store.load_company("TEST") == 3

    saved = store.get_company("TEST")
    assert [row.item for row in saved] == ["revenue", "diluted_eps", "total_liabilities"]
    assert saved[0][:7] == ("TEST", "revenue", date(2018, 9, 29), 100, "USD", "A", "")
    assert saved[1].value == 2.98 and saved[1].unit == "USD/shares"
    assert saved[2].derivation == "liabilities = total − equity"
    assert saved[0].loaded_at == saved[2].loaded_at


def test_reload_replaces_old_rows_without_duplicates(monkeypatch):
    parser_returns(monkeypatch, ROWS)
    store.load_company("TEST")

    parser_returns(monkeypatch, [LineItemRow("revenue", YEAR_END, 110, "NEW", "")])
    store.load_company("TEST")

    assert [(row.item, row.value) for row in store.get_company("TEST")] == [("revenue", 110)]


def test_reload_leaves_other_companies_alone(monkeypatch):
    parser_returns(monkeypatch, ROWS)
    store.load_company("KEEP")
    store.load_company("TEST")
    store.load_company("TEST")
    assert len(store.get_company("KEEP")) == 3


def test_failed_download_keeps_saved_data(monkeypatch):
    parser_returns(monkeypatch, ROWS)
    store.load_company("TEST")

    def fail(ticker):
        raise RuntimeError("SEC is down")

    monkeypatch.setattr(store, "annual_line_items", fail)
    with pytest.raises(RuntimeError):
        store.load_company("TEST")
    assert len(store.get_company("TEST")) == 3


def test_failed_save_undoes_the_whole_load(monkeypatch):
    parser_returns(monkeypatch, ROWS)
    store.load_company("TEST")

    bad_row = LineItemRow("diluted_eps", YEAR_END, None, "A", "")  # value can't be NULL
    parser_returns(monkeypatch, [LineItemRow("revenue", YEAR_END, 999, "A", ""), bad_row])
    with pytest.raises(Exception):
        store.load_company("TEST")

    saved = store.get_company("TEST")
    assert len(saved) == 3 and saved[0].value == 100


def test_empty_parse_keeps_saved_data(monkeypatch):
    parser_returns(monkeypatch, ROWS)
    store.load_company("TEST")

    parser_returns(monkeypatch, [])
    with pytest.raises(ValueError):
        store.load_company("TEST")
    assert len(store.get_company("TEST")) == 3


def test_tickers_are_case_insensitive(monkeypatch):
    parser_returns(monkeypatch, ROWS)
    store.load_company(" test ")
    assert len(store.get_company("TEST")) == 3
    assert len(store.get_company("test")) == 3


def test_unknown_ticker_reads_back_empty():
    assert store.get_company("NOPE") == []
