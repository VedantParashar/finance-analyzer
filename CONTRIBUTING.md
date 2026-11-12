# Contributing

Thanks for helping. This is a student portfolio project, so small, clear changes are valued over big
clever ones. Found a wrong number? An [issue](https://github.com/VedantParashar/finance-analyzer/issues/new/choose)
with the ticker and a screenshot is already a contribution.

## Setup

You need [uv](https://docs.astral.sh/uv/); it installs Python 3.12 and the packages.

```bash
git clone https://github.com/VedantParashar/finance-analyzer.git
cd finance-analyzer
uv sync
cp .env.example .env   # put your own name and email in SEC_USER_AGENT
uv run --env-file .env finance-analyzer
```

The app opens at http://localhost:8501. Downloaded filings and the database go in `data/` (git-ignored).

## Tests

```bash
uv run pytest
```

- Tests never use the network: SEC responses and yfinance are faked.
- Every change to a calculation needs a test with a hand-calculated expected value.
- The same tests, plus a Docker build, run on GitHub Actions for every push and pull request.

## Where things live

| File | Job | Rule |
|---|---|---|
| `edgar.py`, `prices.py` | download from the SEC and Yahoo Finance | the only places that touch the network |
| `schema.py` | which XBRL tags feed each line item | a new tag goes here, with a comment saying which company needs it |
| `parse.py` | turn SEC facts into annual line items | a derived value must say how it was calculated |
| `store.py` | save and read rows in DuckDB | |
| `metrics.py` | the ratios | pure functions, no network or files; return a reason when a value can't be calculated |
| `display.py` | turn results into text | no Streamlit, so it stays easy to test |
| `app.py` | the Streamlit pages | only displays what the engine computes |

## Workflow: one branch and one pull request per change

1. Start from an up-to-date `master`:
   ```bash
   git switch master && git pull
   git switch -c short-description-of-change
   ```
2. Make **one** change. Keep it small enough to review in a few minutes.
3. Run `uv run pytest`.
4. Commit with a message that says what changed, in the present tense
   (e.g. `add fallback tag for interest expense`).
5. Push the branch and open a pull request against `master`. Say what you changed, why, and how you
   checked it. Link the issue it fixes (`Closes #12`).
6. Wait for both checks (`pytest` and `docker`) to pass. `master` is never pushed to directly.

## Fixing a company's data

Most data problems are a missing tag. To investigate one:

1. Load the company in the app and note which line item shows "—" and for which year.
2. Find the tag the company uses in its filing (the SEC's
   [company facts](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) JSON is
   cached in `data/cache/companyfacts/`).
3. Add it to that item's tag list in `schema.py`, after the existing tags, and add a test in
   `tests/test_parse.py`.
4. Check the company's **Data checks** section still balances.
5. Rerun the stress test and check no other company got worse (needs the network):
   ```bash
   uv run --env-file .env python scripts/coverage.py
   git diff docs/COVERAGE.md
   ```
