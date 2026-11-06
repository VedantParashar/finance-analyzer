import json

import pytest

from finance_analyzer import edgar


@pytest.fixture
def fake_cache(tmp_path, monkeypatch):
    """Point the cache at a temp folder holding fake SEC files, with no network allowed."""
    monkeypatch.setattr(edgar, "CACHE_DIR", tmp_path)
    # With no User-Agent, any attempt to download raises, so these tests stay offline.
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    tickers = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
    (tmp_path / "company_tickers.json").write_text(json.dumps(tickers))
    (tmp_path / "companyfacts").mkdir()
    (tmp_path / "companyfacts" / "CIK0000320193.json").write_text('{"entityName": "Apple Inc."}')


def test_get_cik_pads_to_ten_digits_and_ignores_case(fake_cache):
    assert edgar.get_cik(" aapl ") == "0000320193"


def test_get_cik_unknown_ticker_raises(fake_cache):
    with pytest.raises(ValueError, match="Unknown ticker"):
        edgar.get_cik("NOPE")


def test_fetch_company_facts_reads_from_cache(fake_cache):
    assert edgar.fetch_company_facts("AAPL") == {"entityName": "Apple Inc."}
