"""Fetch a company's XBRL "company facts" from SEC EDGAR, cached on disk."""

import json
import os
from pathlib import Path

import httpx

CACHE_DIR = Path("data/cache")
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def _get_json(url: str, cache_path: Path) -> dict:
    """Return JSON from the disk cache, downloading it first if it isn't there."""
    # shortcut: cached files never expire, add a refresh option once new filings matter
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    # The SEC refuses requests that don't name who is asking (name + contact email).
    user_agent = os.environ.get("SEC_USER_AGENT")
    if not user_agent:
        raise RuntimeError(
            'Set SEC_USER_AGENT, e.g. "Finance Analyzer you@example.com", in .env '
            "and run with: uv run --env-file .env ..."
        )

    response = httpx.get(url, headers={"User-Agent": user_agent}, timeout=30)
    response.raise_for_status()  # stop on errors so a bad response is never cached
    data = response.json()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text)
    return data


def get_cik(ticker: str) -> str:
    """Look up a ticker's CIK, zero-padded to the 10 digits the SEC API expects."""
    companies = _get_json(TICKERS_URL, CACHE_DIR / "company_tickers.json")
    wanted = ticker.strip().upper()
    for company in companies.values():
        if company["ticker"] == wanted:
            return f"{company['cik_str']:010d}"
    raise ValueError(f"Unknown ticker: {ticker!r}")


def fetch_company_facts(ticker: str) -> dict:
    """Return the SEC company facts JSON for a ticker."""
    cik = get_cik(ticker)
    return _get_json(FACTS_URL.format(cik=cik), CACHE_DIR / "companyfacts" / f"CIK{cik}.json")
