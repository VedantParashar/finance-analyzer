# Autopilot log

## Summary (2026-11-11)

**Built:** all 8 queue tasks. Metrics (already on master) · CI (pytest + Docker build/health check on
every push and PR) · company page · compare page · learning layer · Excel export with live formulas ·
README · Dockerfile + `docker compose up --build`. 118 tests pass locally and on GitHub Actions.

**Merged:** everything is on master. #7 (CI) was merged first; #8–#12 were closed as included in #13,
which merged the rest of the stack (company page, compare, learning layer, Excel, README, Docker).

**Left in SPEC v1:** price metrics from yfinance (#15); showing the data checks (balance check,
missing years) in the UI (#14).

**Open issues:** #1 absent items vs zero · #2 temporary-equity rule based on Tesla only · #4 cache never
refreshes · #5 LongTermDebt total vs non-current · #6 NVDA FY2026 short-term investments · #14 data checks
in UI · #15 yfinance price metrics.

**The 5 decisions most worth your review:**
1. **Stacked PRs instead of merges.** Claude Code's permission classifier blocked `gh pr merge`, so
   each task became a PR on top of the previous one, and you merged them yourself.
2. **Banks and insurers are detected by SEC SIC code** (6020–6039, 6311–6411). A bank holding company
   filed under another code (e.g. 6199 or 6719) would get no banner.
3. **Excel metric cells are formulas only where the engine could calculate.** Elsewhere they say "n/a",
   with the reason as a comment. This keeps Excel from treating blanks as zero; all 1,407 real formulas
   match the engine. Not opened in real Excel.
4. **The learning text (`learning.json`) was written by Claude** from general finance knowledge. Read
   it before showing it to students, especially the "what's good" ranges.
5. **Compare uses each company's latest fiscal year, with a note when year-ends are more than 31 days
   apart.** KO (Dec 31) vs NVDA (Jan 25) gets no note, even though the labels read FY2025 vs FY2026.
   The column headers show the dates.

Smaller ones: `uv run finance-analyzer` now starts the app; Streamlit usage statistics are switched
off; JSON rather than YAML; no license added (your call; MIT is the usual one); `LEARNING.md` left
untouched, with suggested entries under task 3.

---

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

## Task 7 — README

- **2026-11-11 · decision:** README covers what it is, screenshot placeholders (`docs/screenshots/`),
  setup, run, tests/CI, a mermaid diagram of the actual modules, data sources and limitations linking
  issues #1–#6. Added `.env.example` so setup is `cp .env.example .env`. **Rejected:** real screenshots
  (asked for placeholders).
- **2026-11-11 · decision:** limitations state that share price (yfinance) isn't built yet. **Why:** it's
  in SPEC v1 but wasn't in this queue; better said than implied.
- **2026-11-11 · decision:** "License: no license chosen yet". **Why:** choosing one is the owner's call;
  SPEC says open-source, so MIT is the usual pick for a portfolio project. **Rejected:** adding MIT myself.
- **2026-11-11 · outcome:** docs only; 118 tests still pass.

## Task 8 — Docker

- **2026-11-11 · decision:** `Dockerfile` on `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
  (dependencies installed in their own layer, `--locked --no-dev`), plus `compose.yaml` so it's one
  command: `docker compose up --build`. It reads `.env` and bind-mounts `./data`. **Why:** compose
  handles the env file, port and volume in one place. **Rejected:** a long `docker run` command;
  a named volume (wouldn't share the database with the non-Docker setup).
- **2026-11-11 · decision:** Docker isn't installed on this machine, so the image is verified in a new
  CI job that builds it, starts it and waits for Streamlit's health check. **Rejected:** installing
  Docker Desktop (it needs a licence and account, which the rules forbid).
- **2026-11-11 · decision:** `.dockerignore` keeps `.env`, `data/`, `.git` and tests out of the image.
- **2026-11-11 · outcome:** PR #13: `docker` (≈1 min) and `pytest` checks both pass on GitHub.
- **2026-11-11 · follow-up:** filed #14 (data checks in the UI) and #15 (yfinance price metrics), the
  SPEC v1 items not in this queue.

---

# Session 2 (queue of 7)

Same rules and format. Each branch starts from the previous task's branch, and a branch's log is
closed once the next branch exists.

## S2 Task 1 — MIT license

- **2026-11-11 · decision:** standard MIT text in `LICENSE`, copyright "2026 Vedant Parashar" (the git
  author name). README's License section links to it. Also `license = "MIT"` in `pyproject.toml`, so
  the package metadata agrees with the file. **Rejected:** a license header in every source file (MIT
  doesn't need it).
- **2026-11-11 · outcome:** no code change; 118 tests pass, `uv lock --check` still clean.

## S2 Task 2 — Wider finance banner

- **2026-11-11 · decision:** the banner now covers SIC 6000–6499 (banks, lenders, brokers, insurers).
  Renamed `is_bank_or_insurer` to `is_financial` and the text to "Banks, brokers and insurers", since
  Goldman Sachs (6211) is neither a bank nor an insurer by SIC. **Rejected:** going to 6799 (would
  catch real estate and REITs, which wasn't asked for).
- **2026-11-11 · note:** Visa (7389) and S&P Global (7320) are filed under business services, so they
  still get no banner. SIC codes describe how the SEC files a company, not what students call "finance".
- **2026-11-11 · outcome:** 123 tests pass (boundaries 5999/6000/6499/6500; page test for JPM, GS and
  BRK-B). Real data: JPM (6021), GS (6211) and BRK-B (6331) all load with the banner; AAPL has none.
