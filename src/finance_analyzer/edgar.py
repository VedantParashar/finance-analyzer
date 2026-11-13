"""Fetch a company's XBRL "company facts" from SEC EDGAR, cached on disk."""

import json
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

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
            "and run with: uv run --env-file .env ... (on Streamlit Community Cloud: in the app's Secrets)"
        )

    response = httpx.get(url, headers={"User-Agent": user_agent}, timeout=30)
    response.raise_for_status()  # stop on errors so a bad response is never cached
    response.json()  # same for a page that isn't JSON
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # Written beside the real file and then swapped in, so a page never reads a half-written download.
    partial = cache_path.with_name(f"{cache_path.name}.{threading.get_ident()}.part")
    partial.write_text(response.text)
    partial.replace(cache_path)


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


class Company(NamedTuple):
    ticker: str  # as the SEC writes it, e.g. "BRK-B"
    name: str
    cik: str  # zero-padded to the 10 digits the SEC API expects


class UnknownTicker(ValueError):
    """No company in the SEC's list has this ticker."""


class NoFinancialStatements(ValueError):
    """The SEC lists the ticker but has no financial statement data for it (ETFs, funds, some trusts)."""


def list_companies() -> list[Company]:
    """Every ticker the SEC lists, largest companies first (the SEC's own order)."""
    companies = _get_json(TICKERS_URL, _tickers_path())
    return [Company(c["ticker"], c["title"], f"{c['cik_str']:010d}") for c in companies.values()]


def _compact(text: str) -> str:
    """Letters and digits only, uppercased: "BRK.B", "brk b" and "BRK-B" all become "BRKB"."""
    return "".join(character for character in text.upper() if character.isalnum())


def find_ticker(text: str) -> Company | None:
    """The company whose ticker this is, whatever separator was typed (BRK.B, BRK-B, brk b)."""
    companies = list_companies()
    wanted = text.strip().upper()
    for company in companies:
        if company.ticker == wanted:  # an exact match wins over a look-alike with other punctuation
            return company
    return next((c for c in companies if wanted and _compact(c.ticker) == _compact(wanted)), None)


def search_companies(text: str, limit: int = 8) -> list[Company]:
    """Companies with a name word starting with every word typed, or a ticker starting with it; largest first."""
    words = _words(text)
    start = _compact(text)
    if not start:
        return []

    def name_matches(company: Company) -> bool:
        # Word starts, not anywhere in the name, so "apple" finds Apple but not Pineapple.
        name_words = _words(company.name)
        return all(any(part.startswith(word) for part in name_words) for word in words)

    matches = [c for c in list_companies() if name_matches(c) or _compact(c.ticker).startswith(start)]
    return matches[:limit]


def _words(text: str) -> list[str]:
    """Lowercase words with punctuation dropped: "Coca-Cola Co." gives coca, cola, co."""
    return "".join(character if character.isalnum() else " " for character in text.lower()).split()


def get_cik(ticker: str) -> str:
    """Look up a ticker's CIK, zero-padded to the 10 digits the SEC API expects."""
    company = find_ticker(ticker)
    if company is None:
        raise UnknownTicker(f"No company found for ticker {ticker.strip().upper()!r}.")
    return company.cik


def _update_facts(cik: str, ticker: str) -> None:
    try:
        _update_cache(FACTS_URL.format(cik=cik), _facts_path(cik))
    except httpx.HTTPStatusError as error:
        if error.response.status_code != 404:
            raise
        # The SEC answers "not found" for filers that have never sent financial statements as data.
        raise NoFinancialStatements(
            f"{ticker.strip().upper()} is listed with the SEC but has no financial statements there. "
            "It's probably an ETF or a fund, which this app can't analyse."
        ) from error


def fetch_company_facts(ticker: str) -> dict:
    """Return the SEC company facts JSON for a ticker."""
    cik = get_cik(ticker)
    _update_facts(cik, ticker)
    return json.loads(_facts_path(cik).read_text())


def facts_downloaded_at(ticker: str) -> datetime:
    """When the company's facts were last downloaded, downloading them first if missing or too old."""
    cik = get_cik(ticker)
    _update_facts(cik, ticker)
    return _downloaded_at(_facts_path(cik))


def refresh(ticker: str) -> None:
    """Download everything for a ticker again now. Raises, keeping the old files, if the SEC can't be reached."""
    _update_cache(TICKERS_URL, _tickers_path(), force=True)
    cik = get_cik(ticker)
    _update_cache(FACTS_URL.format(cik=cik), _facts_path(cik), force=True)
    _update_cache(SUBMISSIONS_URL.format(cik=cik), _submissions_path(cik), force=True)


def fetch_company_info(ticker: str) -> dict:
    """The company's name, SIC industry code (a 4-digit number the SEC uses to classify businesses) and exchange."""
    cik = get_cik(ticker)
    data = _get_json(SUBMISSIONS_URL.format(cik=cik), _submissions_path(cik))
    exchange = (data.get("exchanges") or [""])[0] or ""  # e.g. "Nasdaq"; some companies list none
    return {"name": data["name"], "sic": int(data["sic"] or 0), "industry": data["sicDescription"], "exchange": exchange}


def is_financial(sic: int) -> bool:
    """SIC 6000–6499: banks, lenders, brokers and insurers, whose statements don't fit the standard ratios.

    Real estate and holding companies (6500–6799) are left out on purpose.
    """
    return 6000 <= sic <= 6499
