# Autopilot log

## Summary of session 2 (2026-11-11)

**Built:** all 7 queue tasks, each on its own branch and pull request, stacked in this order. Nothing
is merged: merge them top to bottom, or just the last one into `master` once you've read the others.

| # | PR | Branch | What |
|---|---|---|---|
| 1 | #17 | `mit-license` | MIT `LICENSE`, README section |
| 2 | #18 | `widen-finance-banner` | banner for SIC 6000–6499 (JPM, GS, BRK-B tested) |
| 3 | #19 | `data-checks-ui` | balance check per year and missing years on the company page (#14) |
| 4 | #20 | `yfinance-price-metrics` | market cap, P/E, P/B, EV/EBIT, FCF yield (#15) |
| 5 | #21 | `cache-refresh` | 7-day expiry and a "Refresh data" button (#4) |
| 6 | #22 | `streamlit-cloud-deploy` | `streamlit_app.py`, secrets, `DEPLOY.md` |
| 7 | #23 | `readme-screenshots` | real screenshots in `docs/screenshots/` |

148 tests pass locally (118 before). On GitHub, `pytest` and `docker` passed on #17–#21 and `pytest` on
#22 when this was written; #22's second `docker` run and #23 were still running.

**Issues:** #14, #15 and #4 are done but stay open until their PRs reach `master` (GitHub only closes
an issue from a PR merged into the default branch; close them by hand if it doesn't). Still open:
#1, #2, #5, #6.

**SPEC v1:** every item is now built.

**The 5 decisions most worth your review:**
1. **P/E is market cap ÷ net income, not price ÷ EPS** (task 4). Same ratio, but safe when a stock split
   happens after the year-end. All valuation metrics set today's price against the *last fiscal year*,
   so they differ from sites that use the last twelve months. The page says so.
2. **The learning text for the five valuation metrics was written by Claude** (task 4), like the rest of
   `learning.json`. Read the "what's good" ranges before students see them.
3. **A real deployment was not tested** (task 6); it needs your account. No `requirements.txt` was
   added because Streamlit's docs say `uv.lock` is used first. `DEPLOY.md` has the fallback if the
   install fails.
4. **A failed automatic refresh keeps the old data without saying so** (task 5). Only the button
   reports a failure. The caption under the button shows when the data was loaded.
5. **Data checks cover every stored year, and found new failures** (task 3): JPM FY2009 and BRK-B
   FY2014, FY2015, FY2020 and FY2023 don't balance. Both are financial companies (out of scope), so no
   issue was filed. Say if you want one.

Smaller ones: Visa and S&P Global still get no finance banner (their SIC codes are business services);
enterprise value leaves out leases, pensions and minority interests; valuation isn't in the Excel
export; `LEARNING.md` is untouched again, with suggested entries under tasks 4, 5 and 6; the first
session's summary below is unchanged.

---

## Summary of session 1 (2026-11-11)

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

## S2 Task 3 — Data checks on the company page (#14)

- **2026-11-11 · decision:** the page re-reads the SEC download already cached on disk and runs the
  existing `parse.balance_checks` on it (cached per ticker by Streamlit). **Why:** the check needs the
  reported "liabilities and equity" total, which isn't a stored line item. **Rejected:** a new DuckDB
  table for check results (a schema change for something that takes milliseconds to recompute).
- **2026-11-11 · decision:** a "Data checks" section at the bottom of the company page: one summary
  line each for the balance check and missing years, and a table of every stored year (newest first)
  that opens by itself only when a year fails. Each row says what assets were compared with and by how
  much they differ. Years the check can't run say which of the three items is absent.
- **2026-11-11 · decision:** all stored years are checked, not just the five shown. **Why:** older
  years feed the Excel export and 3-year growth rates.
- **2026-11-11 · decision:** a "missing year" is a gap of more than 375 days between stored fiscal year
  ends, the same limit the metrics engine uses, and the line says which ratios it breaks.
  **Not flagged:** a latest year that is simply old (task 5 handles freshness).
- **2026-11-11 · outcome:** 126 tests pass. Real data: AAPL 19 of 20 years balance (FY2007 has no
  balance sheet); TSLA FY2014–15 fail by $58M and $47M (known, #3); GS shows one gap, FY2008 (Nov) to
  FY2009 (Dec), which is its real change of year-end. **New findings, not fixed:** JPM FY2009 and BRK-B
  FY2014, FY2015, FY2020 and FY2023 don't balance. Both are financial companies, out of v1 scope.

## S2 Task 4 — Price metrics from yfinance (#15)

- **2026-11-11 · decision:** new adapter `prices.py` asks yfinance's `fast_info` for the last price and
  market cap. Every failure (unknown symbol, no connection, rate limit, missing or zero values, a
  non-USD quote) becomes one `PriceUnavailable` error with the reason. **Why:** yfinance scrapes Yahoo
  and raises many unrelated error types, so this is the one place a catch-all is right.
- **2026-11-11 · decision:** the five metrics live in the engine as `metrics.price_metrics(rows,
  market_cap)`: pure, no network, same `Metric` shape (value, inputs, reason) as the other ratios. They
  use the latest stored fiscal year.
- **2026-11-11 · decision:** P/E is market cap ÷ net income, not price ÷ EPS. **Why:** it's the same
  ratio, but a stock split after the year-end changes the price and not the stored EPS, which would
  give a wrong P/E; market cap doesn't change in a split. **Rejected:** price ÷ diluted EPS.
- **2026-11-11 · decision:** enterprise value = market cap + short-term debt + long-term debt − cash −
  short-term investments, matching the invested-capital definition already used for ROIC.
  **Left out:** leases, pensions, preferred shares, minority interests (said in the learning text).
- **2026-11-11 · decision:** company page gets a "Valuation at today's price" section of five cards,
  with a caption giving the price, when it was fetched and that the company figures are last fiscal
  year's (so P/E differs from websites using the last twelve months). The compare table gets the same
  five rows. **Not done:** valuation in the Excel export (a price would go stale inside a saved file)
  and in the compare page's over-time chart (there is only today's price).
- **2026-11-11 · decision:** prices are reused for 15 minutes; a failure isn't cached, so the next
  page run tries again. When it fails the cards read "unavailable" with the reason.
- **2026-11-11 · decision:** learning text for the five metrics added to `learning.json`, written by
  Claude like the rest. **Owner should review**, especially the "what's good" ranges.
- **2026-11-11 · outcome:** 139 tests pass; yfinance is mocked in every test. Real data (Nov 11):
  AAPL market cap $5,168,080M, P/E 39.10 (= 5,168,080 ÷ 132,175, checked by hand), FCF yield 2.6%;
  KO P/E 32.02; BRK-B EV/EBIT unavailable (no operating income reported).
  **Not checked:** companies with several share classes (GOOGL), where Yahoo's market cap may not
  cover every class.
- **Suggested for `LEARNING.md`:** *Market cap* = share price × number of shares: the price tag for the
  whole company. *yfinance* = a Python package that reads Yahoo Finance's website; free, but unofficial,
  so the app must cope when it fails. *Mock* = a fake stand-in used in tests (here for yfinance) so
  tests never need the internet.

## S2 Task 5 — Cache refresh (#4)

- **2026-11-11 · decision:** a cached SEC file's age is the file's modified time; older than 7 days
  (`edgar.MAX_AGE`) and it's downloaded again on next use. Applies to all three files (ticker list,
  company facts, company info). **Rejected:** storing download times in the database (the file system
  already knows).
- **2026-11-11 · decision:** if an *automatic* refresh can't reach the SEC, the old copy is used. If the
  *button's* refresh fails, the page shows the error and keeps the saved data. **Why:** stale data
  beats no data, but someone who pressed the button should be told it didn't work.
- **2026-11-11 · decision:** one rule keeps the database in step: the company is parsed and saved again
  whenever the SEC download is newer than its stored rows. The button only re-downloads and clears
  Streamlit's caches; the same rule then reloads the company. **Why:** one code path for the button,
  the 7-day expiry and the first load, and the balance check never reads newer facts than the rows.
- **2026-11-11 · decision:** Streamlit now keeps a loaded company for one day, not forever, so an app
  left running still notices 7-day-old files. The button clears every cached company and price, not
  just this one (one line, and refreshing more is harmless).
- **2026-11-11 · decision:** a caption under the button says when the data was loaded and that it
  refreshes after 7 days. The button is on the company page only.
- **2026-11-11 · outcome:** 146 tests pass (fresh file isn't downloaded; 8-day-old file is; failed
  automatic download keeps the old copy; forced refresh; failed refresh keeps the files; the button
  reloads the rows; the button's failure message). Real data, KO: an artificially 8-day-old file was
  re-downloaded and the rows re-saved on the next view, and the button did both again.
- **Suggested for `LEARNING.md`:** *Stale cache* = a saved copy that's too old to trust. *TTL (time to
  live)* = how long a saved copy may be reused before it's fetched again (here 7 days for SEC files,
  15 minutes for prices).

## S2 Task 6 — Streamlit Community Cloud preparation

- **2026-11-11 · decision:** no new dependency file. **Why:** Streamlit's docs (read today) say
  Community Cloud looks for `uv.lock` first, ahead of `requirements.txt`, and warn against having more
  than one dependency file. **Rejected:** also committing a `requirements.txt` (it would be ignored,
  and would be a second list to keep in step). The fallback command is in DEPLOY.md.
- **2026-11-11 · decision:** new root file `streamlit_app.py` is the cloud's entry point. It adds
  `src/` to Python's search path and calls `app.run()`. **Why:** the docs don't say whether the cloud
  installs the project itself or only its dependencies, and this works either way. `app.py`'s page
  setup moved into a `run()` function so both entry points share it.
- **2026-11-11 · decision:** `SEC_USER_AGENT` is read from `st.secrets` first and copied into the
  environment, where `edgar.py` already looks; with no secrets file the environment (`.env`) is used
  as before. **Why:** keeps `edgar.py` free of Streamlit. `.streamlit/secrets.toml` is git-ignored.
- **2026-11-11 · decision:** DEPLOY.md lists the exact clicks, the one-line secret, how hosting differs
  (temporary disk, Yahoo often blocks cloud servers, usage statistics forced on, anyone can use the
  URL under your SEC identity) and three likely failures with fixes.
- **2026-11-11 · outcome:** 148 tests pass (the cloud entry point runs; secrets win over the
  environment). `streamlit run streamlit_app.py` starts locally and answers its health check.
  **Not checked:** a real deployment (needs the owner's account), so whether `uv.lock` installs cleanly
  there, and that the disk is wiped on restart (commonly reported, not stated in the docs I read).
- **Suggested for `LEARNING.md`:** *Secrets* = settings like passwords or your contact email that a
  hosting service stores for you, outside the code. *Entry point* = the file a tool runs first.

## S2 Task 7 — README screenshots

- **2026-11-11 · decision:** `docs/screenshots/company.png` (AAPL) and `compare.png` (AAPL, KO, NVDA),
  taken from the real app with real SEC data, 1400px wide at 2× sharpness. Each is cropped to the top
  of the page (company: down to the profitability cards; compare: table and chart). **Why:** the full
  company page is about five screens tall and unreadable when shrunk into a README table.
- **2026-11-11 · decision:** the Playwright browser plugin wanted Google Chrome, which isn't installed.
  Used Playwright's Python package through `uvx` (run once, not added to the project) with the Chromium
  already in Playwright's cache on this machine. **Rejected:** installing Chrome; adding Playwright as a
  project dependency for two images.
- **2026-11-11 · decision:** the screenshot script isn't committed. **Why:** it's a one-off; retaking
  them means running the app and saving two browser screenshots.
- **2026-11-11 · outcome:** both images checked by eye, no errors on either page. README's placeholder
  note removed; the image links already pointed at these paths. 148 tests pass.

---

# Session 3 (queue of 4)

Same rules and format as session 2.

## S3 Task 1 — Docs and access

- **2026-11-11 · blocked, not done:** "commit the LEARNING.md I placed in the repo". The only
  `LEARNING.md` on disk is byte-for-byte the one already committed on Nov 6 (git shows no change), and
  no other copy was found in the repo, Downloads, Desktop or Documents. Nothing to commit.
  **Rejected:** writing one myself (the instruction was "as-is"). The suggested entries from session 2
  are still in this log under S2 tasks 4, 5 and 6.
- **2026-11-11 · decision:** README now opens with a "Try it" badge button and the live link, then
  "Use it online", "Run it on your computer" (uv, Docker), "Supported companies" (a four-row table:
  works, works with a warning, may have gaps, doesn't work yet) and "Report a problem". The test
  instructions moved to CONTRIBUTING.md. The badge image is served by shields.io.
- **2026-11-11 · note:** `curl` to the live URL gets a redirect to Streamlit's login handshake, which
  public apps also do, so I couldn't confirm from here that the app is set to public. The README says
  hosted apps go to sleep when unused (well known for Community Cloud, not in the docs I read).
- **2026-11-11 · decision:** CHANGELOG.md has one entry, 1.0.0 dated 2026-11-11, grouped as data,
  metrics, screens, data checks, project and known limits. `pyproject.toml` version went 0.1.0 → 1.0.0
  (and `uv.lock` with it) so the package agrees with the changelog. **Not done:** a git tag or GitHub
  release (not asked for; it would be created from master, which is yours).
- **2026-11-11 · decision:** issue templates are GitHub's form format (`.yml`), so ticker and screenshot
  are required fields on a bug report. They apply the existing `bug` and `enhancement` labels.
- **2026-11-11 · decision:** repo settings changed with `gh repo edit` (this is live now, not part of
  the PR): description "Free app that helps students analyse and compare public companies from SEC
  filings, and teaches what every ratio means."; homepage https://datadough.streamlit.app; topics
  finance, financial-analysis, fundamental-analysis, sec-edgar, xbrl, streamlit, duckdb, python,
  education, students.
- **2026-11-11 · note for the owner:** the `.devcontainer/devcontainer.json` you added uses Python 3.11
  and installs from `requirements.txt`; this project needs Python 3.12 and has no `requirements.txt`,
  so a Codespace would fail to start the app. Left untouched.
- **2026-11-11 · outcome:** docs only; 148 tests pass, `uv lock --check` clean.
