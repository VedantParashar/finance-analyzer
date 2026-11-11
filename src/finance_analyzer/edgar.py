"""Fetch a company's XBRL "company facts" from SEC EDGAR, cached on disk."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

CACHE_DIR = Path("data/cache")
MAX_AGE = timedelta(days=7)  # older cached files are downloaded again, so new filings show up
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


def _downloaded_at(cache_path: Path) -> datetime:
    """When the cached file was last downloaded, as UTC without a timezone (like the database's loaded_at)."""
    return datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).replace(tzinfo=None)


def _update_cache(url: str, cache_path: Path, force: bool = False) -> None:
    """Download the file if it isn't cached, is older than MAX_AGE, or `force` is set."""
    cached = cache_path.exists()
    if cached and not force and datetime.now(UTC).replace(tzinfo=None) - _downloaded_at(cache_path) < MAX_AGE:
        return
    try:
        _download(url, cache_path)
    except httpx.HTTPError:
        # An automatic refresh that fails keeps the old copy: stale data beats no data.
        if not cached or force:
            raise


def _download(url: str, cache_path: Path) -> None:
    # The SEC refuses requests that don't name who is asking (name + contact email).
    user_agent = os.environ.get("SEC_USER_AGENT")
    if not user_agent:
        raise RuntimeError(
            'Set SEC_USER_AGENT, e.g. "Finance Analyzer you@example.com", in .env '
            "and run with: uv run --env-file .env ..."
        )

    response = httpx.get(url, headers={"User-Agent": user_agent}, timeout=30)
    response.raise_for_status()  # stop on errors so a bad response is never cached
    response.json()  # same for a page that isn't JSON
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text)


def _get_json(url: str, cache_path: Path) -> dict:
    """Return JSON from the disk cache, downloading it first if it's missing or too old."""
    _update_cache(url, cache_path)
    return json.loads(cache_path.read_text())


def _tickers_path() -> Path:
    return CACHE_DIR / "company_tickers.json"


def _facts_path(cik: str) -> Path:
    return CACHE_DIR / "companyfacts" / f"CIK{cik}.json"


def _submissions_path(cik: str) -> Path:
    return CACHE_DIR / "submissions" / f"CIK{cik}.json"


def get_cik(ticker: str) -> str:
    """Look up a ticker's CIK, zero-padded to the 10 digits the SEC API expects."""
    companies = _get_json(TICKERS_URL, _tickers_path())
    wanted = ticker.strip().upper()
    for company in companies.values():
        if company["ticker"] == wanted:
            return f"{company['cik_str']:010d}"
    raise ValueError(f"Unknown ticker: {ticker!r}")


def fetch_company_facts(ticker: str) -> dict:
    """Return the SEC company facts JSON for a ticker."""
    cik = get_cik(ticker)
    return _get_json(FACTS_URL.format(cik=cik), _facts_path(cik))


def facts_downloaded_at(ticker: str) -> datetime:
    """When the company's facts were last downloaded, downloading them first if missing or too old."""
    cik = get_cik(ticker)
    _update_cache(FACTS_URL.format(cik=cik), _facts_path(cik))
    return _downloaded_at(_facts_path(cik))


def refresh(ticker: str) -> None:
    """Download everything for a ticker again now. Raises, keeping the old files, if the SEC can't be reached."""
    _update_cache(TICKERS_URL, _tickers_path(), force=True)
    cik = get_cik(ticker)
    _update_cache(FACTS_URL.format(cik=cik), _facts_path(cik), force=True)
    _update_cache(SUBMISSIONS_URL.format(cik=cik), _submissions_path(cik), force=True)


def fetch_company_info(ticker: str) -> dict:
    """The company's name and SIC industry code (a 4-digit number the SEC uses to classify businesses)."""
    cik = get_cik(ticker)
    data = _get_json(SUBMISSIONS_URL.format(cik=cik), _submissions_path(cik))
    return {"name": data["name"], "sic": int(data["sic"] or 0), "industry": data["sicDescription"]}


def is_financial(sic: int) -> bool:
    """SIC 6000–6499: banks, lenders, brokers and insurers, whose statements don't fit the standard ratios.

    Real estate and holding companies (6500–6799) are left out on purpose.
    """
    return 6000 <= sic <= 6499
