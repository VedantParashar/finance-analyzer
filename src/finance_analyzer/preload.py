"""Load a fixed set of companies into the database in the background, so their first view is quick.

Used by the hosted app (streamlit_app.py), whose disk is wiped on every restart. The set is the 30
companies of the stress test in docs/COVERAGE.md.
"""

import time

from finance_analyzer import edgar, store

# Chosen to differ: size, industry, accounting rules, currency, age and profitability.
GROUPS = {
    "Mega caps": ["MSFT", "GOOGL", "AMZN", "META"],
    "Small and mid caps": ["PLOW", "CALM", "CROX"],
    "Retail": ["WMT", "COST", "TGT", "HD"],
    "Energy": ["XOM", "CVX", "OXY"],
    "Pharma": ["PFE", "LLY", "MRNA"],
    "Utilities": ["NEE", "DUK"],
    "REITs": ["O", "PLD", "AMT"],
    "Foreign filers": ["NVO", "SHEL", "CNQ", "BABA", "SONY"],
    "Recent IPOs": ["RDDT", "CRWV"],
    "Loss-making": ["RIVN"],
}
TICKERS = [ticker for tickers in GROUPS.values() for ticker in tickers]
PAUSE = 0.5  # seconds between companies: the SEC allows 10 requests a second, this stays far below


def run(tickers: list[str] = TICKERS) -> dict[str, str]:
    """Load every listed company that isn't stored yet; returns {ticker: why it failed}.

    One company failing (ExxonMobil has no annual data in the SEC's feed) never stops the rest.
    """
    started, failed = time.monotonic(), {}
    missing = [ticker for ticker in tickers if ticker not in store.stored_tickers()]
    for ticker in missing:
        try:
            store.load_company(ticker)
            edgar.fetch_company_info(ticker)  # the page asks for this too; fetch it now, not on first view
        except Exception as error:  # a background job has nobody to show an error to, so note it and go on
            failed[ticker] = f"{type(error).__name__}: {error}"
        time.sleep(PAUSE)
    # Printed so it shows up in the hosting log (Streamlit Community Cloud: Manage app → logs).
    print(
        f"Pre-load: {len(missing) - len(failed)} of {len(missing)} missing companies loaded in "
        f"{time.monotonic() - started:.0f}s; failed: {failed or 'none'}",
        flush=True,
    )
    return failed
