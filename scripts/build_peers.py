"""Rebuild src/finance_analyzer/peers.json: each ticker's SIC industry code and latest annual revenue.

The peer suggestions on the company page read that file, so the app never downloads this itself.
Run it about once a year, after most annual reports are in:

    uv run --env-file .env python scripts/build_peers.py

It downloads about 280 MB from the SEC (four quarterly "Financial Statement Data Sets", for the SIC
codes) plus one small file per revenue tag (the "frames" API: one fact for every company at once).
"""

import csv
import io
import json
import math
import os
import zipfile
from datetime import date
from pathlib import Path

import httpx

from finance_analyzer import edgar
from finance_analyzer.schema import ITEMS

OUTPUT = Path(__file__).parents[1] / "src" / "finance_analyzer" / "peers.json"
DATA_SETS = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{year}q{quarter}.zip"
FRAMES = "https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/CY{year}.json"


def last_four_quarters(today: date) -> list[tuple[int, int]]:
    """The four most recent finished quarters, newest first: every annual filer reports in one of them."""
    year, quarter = today.year, (today.month - 1) // 3  # the quarter before the current one; 0 = last year's Q4
    quarters = []
    for _ in range(4):
        if quarter == 0:
            year, quarter = year - 1, 4
        quarters.append((year, quarter))
        quarter -= 1
    return quarters


def sic_codes(client: httpx.Client, today: date) -> dict[int, int]:
    """CIK → SIC code, from the filings list (sub.txt) in each quarterly data set; the newest filing wins."""
    codes: dict[int, int] = {}
    for year, quarter in last_four_quarters(today):
        response = client.get(DATA_SETS.format(year=year, quarter=quarter))
        if response.status_code == 404:  # the newest quarter isn't published yet
            continue
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive, archive.open("sub.txt") as file:
            for row in csv.DictReader(io.TextIOWrapper(file, "utf-8"), delimiter="\t"):
                if row["sic"]:
                    codes.setdefault(int(row["cik"]), int(row["sic"]))
        print(f"{year}q{quarter}: {len(codes)} companies with a SIC code so far")
    return codes


def revenues(client: httpx.Client, year: int) -> dict[int, float]:
    """CIK → revenue in US dollars for the fiscal year closest to a calendar year; schema tag order decides."""
    by_tag: list[dict[int, float]] = []
    for tag in ITEMS["revenue"].tags:
        response = client.get(FRAMES.format(tag=tag, year=year))
        if response.status_code == 404:  # nobody used this tag that year
            continue
        response.raise_for_status()
        by_tag.append({fact["cik"]: fact["val"] for fact in response.json()["data"]})
    found: dict[int, float] = {}
    for values in by_tag:
        for cik, value in values.items():
            found.setdefault(cik, value)
    for cik, value in found.items():
        # A few filers tag the same revenue twice, once a thousand or a million times too large
        # (Tigo Energy, FY2025: $103.5M also filed as $103.5bn). Believe the smaller figure.
        others = [values[cik] for values in by_tag if cik in values]
        found[cik] = next((o for o in others for scale in (1e3, 1e6) if math.isclose(o * scale, value, rel_tol=0.001)), value)
    return found


def main() -> None:
    today = date.today()
    with httpx.Client(headers={"User-Agent": os.environ["SEC_USER_AGENT"]}, timeout=300) as client:
        codes, revenue = sic_codes(client, today), revenues(client, today.year - 1)
    peers, seen = {}, set()
    for company in edgar.list_companies():  # largest first, so a company's main share class comes first
        cik = int(company.cik)
        if cik in seen or cik not in codes or revenue.get(cik, 0) <= 0:
            continue
        seen.add(cik)
        peers[company.ticker] = [codes[cik], revenue[cik]]
    OUTPUT.write_text(json.dumps({"revenue_year": today.year - 1, "companies": peers}, separators=(",", ":")) + "\n")
    print(f"Wrote {len(peers)} companies to {OUTPUT}")


if __name__ == "__main__":
    main()
