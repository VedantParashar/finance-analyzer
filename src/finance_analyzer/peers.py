"""Peer suggestions: companies in the same SEC industry (SIC code) with the closest revenue.

Reads peers.json, a list of every ticker's SIC code and latest annual revenue in US dollars, rebuilt
about once a year by scripts/build_peers.py. Nothing here touches the network.
"""

import json
import math
from collections.abc import Collection
from pathlib import Path
from typing import NamedTuple

_FILE = json.loads(Path(__file__).with_name("peers.json").read_text())
REVENUE_YEAR: int = _FILE["revenue_year"]
COMPANIES: dict[str, list] = _FILE["companies"]  # ticker -> [SIC code, revenue]; one ticker per company


class Peer(NamedTuple):
    ticker: str
    revenue: float  # US dollars, for the fiscal year closest to REVENUE_YEAR
    same_code: bool  # True = same 4-digit SIC code, False = only the same 3-digit group


def suggest(tickers: Collection[str], sic: int, limit: int = 5) -> list[Peer]:
    """Up to `limit` peers for a company: same 4-digit SIC code first, topped up from its 3-digit group.

    `tickers` is every ticker of the company itself (GOOGL and GOOG), so it never suggests itself.
    Within each group the closest revenue comes first; if the company's own revenue isn't in the file
    (it reports in another currency, say), the largest come first instead.
    """
    if not sic:
        return []
    own = next((COMPANIES[ticker][1] for ticker in tickers if ticker in COMPANIES), None)

    def distance(revenue: float) -> float:
        # Ratios, not differences: half the size and double the size are equally far away.
        return abs(math.log(revenue / own)) if own else -revenue

    group = [
        Peer(ticker, revenue, code == sic)
        for ticker, (code, revenue) in COMPANIES.items()
        if code // 10 == sic // 10 and ticker not in tickers
    ]
    return sorted(group, key=lambda peer: (not peer.same_code, distance(peer.revenue)))[:limit]
