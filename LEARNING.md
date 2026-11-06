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
XBRL facts = company → taxonomy (dei/us-gaap) → concept → unit → data points
No start = balance-sheet snapshot; start+end = flow over a period
Never trust fy; use the dates
The same number appears in several filings, so deduplicate
quarterly vs year-to-date periods · Q4 = FY − 9 months · tag names change over time (ASC 606) · 52/53-week fiscal years.