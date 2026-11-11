import json
import os
import time
from datetime import UTC, datetime

import httpx
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


def test_fetch_company_info_reads_name_and_industry(fake_cache, tmp_path):
    (tmp_path / "submissions").mkdir()
    submissions = {"name": "Apple Inc.", "sic": "3571", "sicDescription": "Electronic Computers"}
    (tmp_path / "submissions" / "CIK0000320193.json").write_text(json.dumps(submissions))
    assert edgar.fetch_company_info("AAPL") == {"name": "Apple Inc.", "sic": 3571, "industry": "Electronic Computers"}


@pytest.mark.parametrize(
    "sic, expected",
    [
        (6021, True),  # JPMorgan: national commercial bank
        (6211, True),  # Goldman Sachs: security broker/dealer
        (6331, True),  # Berkshire Hathaway: fire, marine & casualty insurance
        (6000, True),
        (6499, True),
        (5999, False),
        (6500, False),  # real estate starts here
        (3571, False),  # Apple
    ],
)
def test_financial_companies_by_sic(sic, expected):
    assert edgar.is_financial(sic) is expected


FACTS = "companyfacts/CIK0000320193.json"


def make_old(path, days):
    then = time.time() - days * 86400
    os.utime(path, (then, then))


@pytest.fixture
def sec(monkeypatch):
    """A fake SEC: records each URL asked for and answers with new JSON, or fails if .fail is set."""

    class FakeSEC:
        calls: list[str] = []
        fail = False

        def get(self, url, **kwargs):
            self.calls.append(url)
            if self.fail:
                raise httpx.ConnectError("no connection")
            tickers = '{"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}'
            return httpx.Response(200, text=tickers if "tickers" in url else '{"entityName": "new"}', request=httpx.Request("GET", url))

    fake = FakeSEC()
    fake.calls = []
    monkeypatch.setenv("SEC_USER_AGENT", "Test test@example.com")
    monkeypatch.setattr(edgar.httpx, "get", fake.get)
    return fake


def test_cache_younger_than_seven_days_is_used(fake_cache, tmp_path, sec):
    make_old(tmp_path / FACTS, days=6)
    assert edgar.fetch_company_facts("AAPL") == {"entityName": "Apple Inc."}
    assert sec.calls == []


def test_cache_older_than_seven_days_is_downloaded_again(fake_cache, tmp_path, sec):
    make_old(tmp_path / FACTS, days=8)
    assert edgar.fetch_company_facts("AAPL") == {"entityName": "new"}
    assert sec.calls == [edgar.FACTS_URL.format(cik="0000320193")]
    assert (datetime.now(UTC).replace(tzinfo=None) - edgar.facts_downloaded_at("AAPL")).total_seconds() < 60


def test_old_cache_is_kept_when_the_automatic_download_fails(fake_cache, tmp_path, sec):
    make_old(tmp_path / FACTS, days=8)
    sec.fail = True
    assert edgar.fetch_company_facts("AAPL") == {"entityName": "Apple Inc."}


def test_refresh_downloads_fresh_files_again(fake_cache, sec):
    edgar.refresh("AAPL")
    assert len(sec.calls) == 3  # ticker list, company facts, company info
    assert edgar.fetch_company_facts("AAPL") == {"entityName": "new"}


def test_failed_refresh_raises_and_keeps_the_old_files(fake_cache, sec):
    sec.fail = True
    with pytest.raises(httpx.ConnectError):
        edgar.refresh("AAPL")
    assert edgar.fetch_company_facts("AAPL") == {"entityName": "Apple Inc."}
