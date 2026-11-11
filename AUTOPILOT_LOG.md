# Autopilot log

Decisions made without asking during the autopilot session, one entry per decision.
Format: date · task · decision · why · alternatives rejected.

## Task 1 — Metrics module

- **2026-11-11 · outcome:** already built, tested (78 tests passing) and merged as c026d77 before this session
  started, so no new branch. Apple FY2026 inventory (5,718 → 14,541M) was verified then as the fiscal
  year-end `InventoryNet` balance from the FY2026 10-K.

## Task 2 — GitHub Actions CI

- **2026-11-11 · decision:** one workflow, `uv run --locked pytest`, on every push and PR, using
  `astral-sh/setup-uv`. **Why:** uses the same command as locally; `--locked` fails if `uv.lock` is
  out of date with `pyproject.toml`. **Rejected:** a Python version matrix (the project pins 3.12 only);
  adding lint (not asked for).
- **2026-11-11 · decision:** log entries ride on each task's branch and reach master through its PR.
  **Why:** the hard rule bans pushing to master directly. **Rejected:** a separate log-only PR per task
  (doubles the PRs for no gain).
- **2026-11-11 · outcome:** PR #7 open, `pytest` check passed on GitHub (78 tests, ~12s).
  **Blocked:** `gh pr merge --squash` was denied by Claude Code's permission classifier ("merge without
  review"). **Decision:** don't work around it; build every later task on a branch stacked on the
  previous one, each PR targeting the previous task's branch so its diff shows only that task.
  **Why:** later tasks need earlier code (the compare page needs app.py). **Rejected:** branching every
  task from master (would leave tasks 4–6 without the code they build on); stopping the queue.
  The owner merges the stack in order (see the summary at the top).

## Task 3 — Single-company Streamlit page

- **2026-11-11 · decision:** app lives at `src/finance_analyzer/app.py`; `uv run finance-analyzer` now
  starts it (was a hello-world). **Why:** keeps all code in the package and keeps the run command in
  CLAUDE.md working. **Rejected:** `app.py` at the repo root (a second code location).
- **2026-11-11 · decision:** bank/insurer detection by SEC SIC code (6020–6039 banks, 6311–6411
  insurers) from the SEC submissions API, read through the existing disk cache. **Why:** the SEC's own
  classification, no extra service. **Rejected:** a `companies` table in DuckDB (the disk cache already
  means one download per company); a hard-coded ticker list. **Risk:** a bank holding company filed
  under another code (e.g. 6199, 6719) won't get the banner.
- **2026-11-11 · decision:** formula text in `metrics.py` (`FORMULA_TEXT`) beside `FORMULAS`, with a
  test that the keys match. Formatting lives in a new Streamlit-free `display.py` so it's unit-tested.
- **2026-11-11 · decision:** the formula expander shows the formula in words, then every entry of
  `Metric.inputs` with its value, then the result. **Why:** generic for all 19 metrics. **Rejected:**
  hand-written substituted formulas per metric (19 templates to keep in sync).
- **2026-11-11 · decision:** YoY change shown as percentage points for ratios, × for multiples, % for
  free cash flow; debt/equity colours a rise red.
- **2026-11-11 · decision:** one `st.cache_data` function returns rows, metrics and company info, and
  loads from the SEC on first view. Cached for the app's lifetime (shortcut comment in code; matches
  issue #4). Errors (unknown ticker, no `SEC_USER_AGENT`, network) show as `st.error`, never a crash.
- **2026-11-11 · decision:** `.streamlit/config.toml` turns off Streamlit's anonymous usage statistics.
  **Why:** the app should keep everything local.
- **2026-11-11 · decision:** didn't edit `LEARNING.md` (the owner's own notes). Suggested entries:
  Streamlit (Python script → web page, reruns top to bottom on every click), Plotly (interactive
  charts), `st.cache_data` (remembers a function's result), SIC code (the SEC's 4-digit industry code).
- **2026-11-11 · outcome:** 108 tests pass, including 4 `AppTest` smoke tests (offline, temp database).
  Rendered against the real database: AAPL, KO, TSLA, NVDA, JPM all load with no exception; JPM shows
  the banner. `uv run finance-analyzer --server.headless true` starts and `/_stcore/health` returns ok.

## Task 4 — Compare page

- **2026-11-11 · decision:** two pages through `st.navigation`; the navigation runs only under
  `if __name__ == "__main__"` so tests can import a page function and run it with `AppTest.from_function`.
  **Why:** `AppTest.switch_page` only supports file-based pages. **Rejected:** one file per page plus a
  shared helper module (three files for what fits in one).
- **2026-11-11 · decision:** the table compares each company's *latest* fiscal year, with the year and
  end date in the column header (e.g. `NVDA FY2026 (Jan 25)`); missing values show "—" with the reasons
  in an expander. **Rejected:** forcing a common calendar year (would hide a company's newest year).
- **2026-11-11 · decision:** the year-end note appears when the latest year-ends are more than 31 days
  apart. **Why:** days, not months, so 52/53-week drift (Sep 26 vs Sep 30) doesn't trigger it; KO
  (Dec 31) vs NVDA (Jan 25) is 25 days and mostly the same period, so no note.
- **2026-11-11 · decision:** one overlaid chart driven by a metric selector, x-axis = real year-end
  dates. **Rejected:** a fixed set of overlaid charts (the selector covers all 18).
- **2026-11-11 · decision:** DuPont left out of the compare table (it equals ROE, already a row).
- **2026-11-11 · outcome:** 114 tests pass (3 new compare smoke tests). Real data: "AAPL, KO, NVDA"
  shows the year-end note and AAPL ROE 142.3% / KO 46.0% (match the hand-calculated tests);
  "TSLA JPM" shows no note and JPM's banner. Headless server starts, health ok.

## Task 5 — Learning layer

- **2026-11-11 · decision:** JSON, not YAML, at `src/finance_analyzer/learning.json`. **Why:** Python
  reads JSON with no new dependency; living in the package means it ships in the wheel (checked).
  **Rejected:** YAML (needs PyYAML for nicer multi-line text); a `docs/` folder (not packaged).
- **2026-11-11 · decision:** text shown inside each card's "Formula and meaning" expander, after the
  filled-in formula, and in the DuPont section. **Rejected:** always-visible text (19 cards × 3
  paragraphs buries the numbers).
- **2026-11-11 · decision:** "what's good" gives industry-dependent ranges and says to compare with
  peers, and traps mention this app's own limits (Apple's missing interest expense, LongTermDebt issue
  #5, the never-reported-means-zero rule). **Owner should review:** the text is general finance
  knowledge written by Claude, not checked against a textbook.
- **2026-11-11 · outcome:** 115 tests pass (new: every metric has all three non-empty texts; the
  company page shows them). Real data renders for all five; headless start ok.

## Task 6 — Excel export with live formulas

- **2026-11-11 · decision:** a metric cell gets a formula only when the engine calculated that year;
  otherwise it says "n/a" with the engine's reason as a cell comment. **Why:** Excel would otherwise
  treat blanks as 0 and show wrong numbers or #DIV/0!, and this keeps one source of truth for the
  rules (consecutive years, negative equity…). **Rejected:** `IF(ISBLANK(…))` guards in every formula
  (would re-implement the engine's rules in Excel and drift from them).
- **2026-11-11 · decision:** every stored year is exported, not just the last 5, so averages and
  3-year CAGRs have their earlier years. Line items in $M (EPS in $, shares in millions); ratios don't
  change with the scale, free cash flow is labelled "in $M".
- **2026-11-11 · decision:** every schema item gets a row even when empty, so formulas never point at
  a missing row; never-reported inventory/debt/short-term investments are filled with 0 plus a comment,
  matching the engine. Derivations become cell comments. DuPont's cell multiplies the three metric
  cells above it, so it's live too.
- **2026-11-11 · decision:** download button on the company page; the file is built on every page run
  (~17KB, milliseconds). **Rejected:** caching it (not worth the code).
- **2026-11-11 · outcome:** 118 tests pass; the export test evaluates every formula in Python and checks
  it equals the engine's value. Real data: 1,407 formulas across AAPL/KO/TSLA/NVDA/JPM, 0 mismatches.
  **Not checked:** opening in real Excel/LibreOffice (not installed here); the formulas use only `+ - * /
  ^`, parentheses and `'Line items'!C5`-style references, which every spreadsheet app supports.
