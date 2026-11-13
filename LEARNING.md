uv= Manage Python + packages
CLAUDE.md = standing instructions for claude
.gitignore = files git should not save eg vinv
File	Who it’s for
main.py	the computer (your code)
pyproject.toml, uv.lock, .python-version, .venv/	uv (setup and dependencies)
.gitignore, .git/	Git (version history)
CLAUDE.md	Claude
README.md	visitors on GitHub
LEARNING.md	you
CIK: the SEC’s permanent ID number for a company. Tickers can change; the CIK doesn’t.
User-Agent: a “who’s asking” label sent with every web request.
Environment variable / .env: settings and secrets kept outside the code, so the code can be public.
Cache: a saved copy of downloaded data, so it’s fast and doesn’t overload the SEC’s servers.
Market cap: share price × number of shares, the price tag for the whole company.
yfinance: a Python package that reads Yahoo Finance’s website. Free but unofficial, so the app must cope when it fails.
Mock: a fake stand-in used in tests (here for yfinance), so tests never need the internet.
Stale cache: a saved copy that’s too old to trust.
TTL (time to live): how long a saved copy may be reused before it’s fetched again (7 days for SEC files, 15 minutes for prices).
Secrets: settings like passwords or your contact email that a hosting service stores for you, outside the code.
Entry point: the file a tool runs first.
Normalization: turning different spellings of the same thing (BRK.B, brk b) into one standard form before looking it up.
Autocomplete: suggestions that narrow as you type.
IFRS: the accounting rules used in most countries outside the US (the US uses US GAAP).
20-F: the annual report a foreign company files with the SEC, like a 10-K.
Reporting currency: the currency a company’s statements are written in.
ADR: a US-listed share that stands for shares of a foreign company.
Exchange rate pair: TWD=X means “Taiwan dollars per one US dollar”. To compare a dollar market cap with profits in Taiwan dollars, both must be in the same currency first.
Accrual: profit counts a sale when it’s made, cash flow when the money arrives. The gap between the two is accruals; a big gap means profit is ahead of cash.
SIC code: a 4-digit industry number the SEC gives every filer. The first 3 digits are a wider group, the first 2 wider still (20 = food, 2080 = beverages).
TTM (trailing twelve months): the last four quarters added together, so the figure is always a full year but as fresh as the latest quarterly report.
Median: line the values up in order and take the middle one. Unlike an average, one extreme company can’t drag it.
XBRL facts = company → taxonomy (dei/us-gaap) → concept → unit → data points
No start = balance-sheet snapshot; start+end = flow over a period
Never trust fy; use the dates
The same number appears in several filings, so deduplicate
quarterly vs year-to-date periods · Q4 = FY − 9 months · tag names change over time (ASC 606) · 52/53-week fiscal years.