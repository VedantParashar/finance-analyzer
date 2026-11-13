# Autopilot log

## Summary of session 6 (2026-11-13)

**Built:** 5 of 6 queue tasks, each on its own branch and pull request, stacked in this order; task 1
was skipped as the queue allowed. Nothing is merged.

| # | PR | Branch | What |
|---|---|---|---|
| 1 | (#49) | — | pre-load opt-in: **skipped**, no sign of memory trouble (logged in #49) |
| 2 | #49 | `coverage-rerun` | `docs/COVERAGE.md` rerun with red-flag availability and the five new line items |
| 3 | #50 | `learning-notes` | 18 suggested terms added to `LEARNING.md`, no existing text changed |
| 4 | #51 | `release-notes-1.2.0` | CHANGELOG 1.2.0 for session 5; version 1.2.0; `uv lock` |
| 5 | #52 | `tygo-revenue-scale` | revenue tagged 1,000× too large by a second tag: the smaller is used and labelled |
| 6 | #53 | `red-flags-compare-excel` | red-flag scores on the compare page and in the Excel export |

277 tests pass locally (271 before).

**Worth your attention:**
1. **The live app asks for a login.** https://datadough.streamlit.app redirects to a Streamlit login
   page, so visitors following the README can't use it. If that isn't intended, check the app's
   sharing settings at share.streamlit.io. It's also why I couldn't check the live app's memory
   (task 1): locally, the full pre-load adds about 25 MB at its peak (201 MB against 176 MB).
2. **Excel: Piotroski F and Beneish M are values, not formulas** (task 6), with every input in the
   cell comment. Altman Z″ and the accruals ratio are live formulas.
3. **1.2.0 is dated 2026-11-13 and covers session 5 only** (task 4); this session's changes would go in
   the next version. No git tag.
4. **The scale-slip rule covers revenue only** (task 5), as asked; only Tigo Energy changed among 41
   companies checked row by row.
5. **Coverage:** nothing that was measured before changed. Red-flag scores are available for 18–20 of
   29 companies (accruals ratio for all 29); every gap comes from a missing line item, mostly known
   issues #29, #31, #33 and #1.

---

## Summary of session 5 (2026-11-12)

**Built:** all 6 queue tasks, each on its own branch and pull request, stacked in this order. Nothing
is merged. `pytest` and `docker` pass on GitHub for all six.

| # | PR | Branch | What |
|---|---|---|---|
| 1 | #43 | `red-flag-scores` | Altman Z″, Piotroski F, Beneish M, accruals ratio, per year, "Red flags" section |
| 2 | #44 | `peer-suggestions` | 5 peers by SIC code and revenue closeness, one click to compare |
| 3 | #45 | `quarterly-ttm` | quarters (Q4 = FY − 9M), TTM, Period toggle on the company page |
| 4 | #46 | `industry-benchmarks` | median per metric across stored companies in the same 2-digit SIC group |
| 5 | #47 | `shareable-links` | `?ticker=AAPL`, `?compare=AAPL,KO` |
| 6 | #48 | `preload-stress-companies` | background pre-load of the 30 stress-test companies on the hosted app; timings |

271 tests pass locally (220 before).

**The 5 decisions most worth your review:**
1. **Altman Z is the Z″ version** (task 1): the classic score needs a share price for every past year.
   Cut-offs are 2.6 and 1.1 and the numbers won't match finance sites.
2. **Peers come from a file shipped with the app** (task 2), `peers.json`, rebuilt about once a year
   with `scripts/build_peers.py`. Revenue in it is a year old by design.
3. **TTM is fed through the annual rules and not saved in the database** (task 3). Foreign filers have
   no quarterly data and stay annual. Three real-data bugs were found and fixed on the way (Amazon,
   Costco, split dating).
4. **Industry medians need 3 stored companies** (task 4) and the sample is whatever is in the database.
5. **Pre-load saves about a second, not more** (task 6), measured on my machine only. See S5 task 6.

**Not done (not in the queue):** `CHANGELOG.md` has no entries for this session, and
`docs/COVERAGE.md` wasn't rerun, so it doesn't list the five line items added in task 1.

`SPEC.md` changed in tasks 1–5: red-flag scores, quarterly data, peers, benchmarks and links were all
outside the written v1 scope.

---

## Summary of session 4 (2026-11-12)

**Built:** all 6 queue tasks, each on its own branch and pull request, stacked in this order. Nothing
is merged.

| # | PR | Branch | What |
|---|---|---|---|
| 1 | #35 | `compare-exact-ticker` | compare page: typing a ticker and pressing Enter always picks that ticker |
| 2 | #36 | `tsmc-ifrs-bonds` | TSMC's bonds counted as debt (#26): debt/equity 0.24×, was 0.02× |
| 3 | #38 | `foreign-valuation` | P/E, P/B, EV/EBIT, FCF yield for foreign filers; market cap converted, rate and date shown |
| 4 | #39 | `remove-devcontainer` | `.devcontainer` deleted |
| 5 | #40 | `accept-40-f-a` | 40-F/A accepted |
| 6 | #41 | `release-notes-1.1.0` | CHANGELOG: 1.1.0 notes; 1.0.0 now covers everything up to session 3 |

220 tests pass locally (190 before).

**Already live (not waiting for a merge):** one new issue, #37 (TSMC's FY2025 statements are missing
from the SEC's data feed).

**The 5 decisions most worth your review:**
1. **Task 2 doesn't do exactly what you asked.** You said to add bonds to debt for every IFRS filer.
   Novo Nordisk (IFRS) tags its bonds *inside* its borrowings figure, so that would have doubled its
   long-term debt (DKK 230bn shown, 119bn true). Bonds are added only when they are larger than the
   borrowings figure, which proves they aren't part of it. TSMC is fixed; of 40 companies compared row
   by row, only TSMC changed. A company whose separate bonds are smaller than its bank loans would
   still be understated; none of the 11 IFRS companies I looked at has that shape.
2. **TSMC's valuation ratios use FY2024 profit** (task 3, #37): the SEC's feed has nothing from its
   FY2025 report, so its P/E reads 61×, higher than finance sites show. Found while checking task 3;
   filed, not fixed.
3. **Compare-page name search got narrower** (task 1). To make an exact ticker always win, the box now
   matches from the start of each entry. Every company is listed twice (ticker first, name first), so
   "Coca" still suggests Coca-Cola, but "Hathaway" suggests nothing; typing it and pressing Enter still
   gets the "did you mean BRK-B" message. Also "AAP" + Enter now picks Advance Auto Parts, not Apple.
4. **Currency conversion was out of scope in `SPEC.md`** (task 3). I changed the spec in the same PR:
   market cap is converted for valuation; statements still aren't. Toyota's FCF yield stays
   unavailable (no capital expenditure, #27), so "works for TM" is 3 of 4 ratios.
5. **`.devcontainer` was deleted, not fixed** (task 4): Streamlit Cloud doesn't read it, and a fixed one
   can't be tested without opening a Codespace on your account. The log lists what a working one needs.

Smaller ones: the 1.1.0 changelog heading says "not released yet" and `pyproject.toml` still says
1.0.0, so releasing means setting the date, bumping the version and tagging; 1.0.0's date moved to
2026-11-12, the day session 3 was merged; I used `EUR=X` rather than your `EURUSD=X` example because it
is quoted the same way round as `TWD=X`; 40-F/A is covered by a unit test only (no downloaded company
has one); `LEARNING.md` suggestion under S4 task 3.

---

## Summary of session 3 (2026-11-12)

**Built:** all 4 queue tasks, each on its own branch and pull request, stacked in this order. Nothing
is merged.

| # | PR | Branch | What |
|---|---|---|---|
| 1 | #24 | `docs-and-access` | live link and "Try it" button, README sections, CONTRIBUTING, CHANGELOG, issue templates |
| 2 | #25 | `ticker-search` | search by ticker or name with suggestions, BRK.B-style normalization, clearer errors, examples |
| 3 | #28 | `foreign-filers` | 20-F/40-F, IFRS tags for all 23 items, reporting currency, SPEC scope |
| 4 | #34 | `stress-test-coverage` | 30-company stress test, `docs/COVERAGE.md`, five data fixes |

190 tests pass locally (148 before). `pytest` and `docker` passed on GitHub for #24 and #25 when this
was written; #28 and #34 were still running (both passed afterwards).

**Not done:** committing your `LEARNING.md`. The copy on disk is identical to the one committed on
Nov 6, so there was nothing to commit. If you saved a new one somewhere else, tell me where.

**Already live (not waiting for a merge):** the repo's description, homepage and topics, and seven new
issues (#26, #27, #29–#33).

**Stress test in one line:** 29 of 30 companies load; 8 have every metric; ExxonMobil can't be loaded
because the SEC's data feed only has its quarterly reports (#32).

**The 5 decisions most worth your review:**
1. **Foreign filers get no valuation ratios** (task 3). Their statements are in TWD, EUR or JPY and
   Yahoo's market cap is in dollars; you asked for no conversion yet, so P/E, P/B, EV/EBIT and FCF
   yield read "unavailable" for them rather than showing a wrong number.
2. **TSMC's debt is wrong on screen** (task 3, #26): debt/equity shows 0.02× where about 0.25× is
   right, because its bonds are tagged apart from its borrowings and adding them could double-count at
   other companies. Toyota has no gross margin or free cash flow (#27).
3. **Two calculated fallbacks were added in the stress test** (task 4), beyond "a missing tag": cash
   including restricted cash where plain cash isn't tagged, and shareholders' equity as total equity
   less minority interest. Both are labelled on screen as calculated.
4. **Typing on the compare page can still pick the wrong company for one- and two-letter tickers**
   (tasks 2 and 3): "F" or "MA" plus Enter chooses a larger company containing those letters. Picking
   from the list always works; the company page isn't affected.
5. **The page tests patch a private part of Streamlit's test harness** (task 2) so that typed tickers
   and names can be tested. A Streamlit upgrade could break those tests, not the app.

Smaller ones: version bumped to 1.0.0 to match the changelog, no git tag or release made; 40-F/A is not
an accepted form (not requested); your `.devcontainer` uses Python 3.11 and `requirements.txt`, which
this project doesn't have, so a Codespace won't start the app; I couldn't confirm from here that
https://datadough.streamlit.app is set to public; `LEARNING.md` suggestions are under S3 tasks 2 and 3.

---

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

## S3 Task 2 — Ticker search and normalization

- **2026-11-11 · decision:** the ticker text boxes became Streamlit search boxes (`st.selectbox` on the
  company page, `st.multiselect` capped at 4 on compare) filled with every company in the SEC's list
  as "AAPL — Apple Inc.", largest first (the SEC's own order). They filter as you type and also accept
  text that isn't in the list. **Why:** it's Streamlit's built-in autocomplete, so no extra package.
  **Rejected:** a text box plus a "did you mean" list after pressing Enter (no suggestions while typing);
  a third-party search-box component. **Checked:** 10,405 options load in under a second and suggest
  within a second in a real browser.
- **2026-11-11 · decision:** typed text is matched to the SEC's form by comparing letters and digits
  only, so BRK.B, BRK-B, brk b, BRK/B and brkb all find BRK-B. An exact match wins first. **Why:** the
  SEC's list isn't consistent itself (`BRK-B` but `SHO.PRI`), so swapping one separator for another
  would break some tickers.
- **2026-11-11 · decision:** text that isn't a ticker is searched in company names: every typed word
  must start a word of the name ("apple" finds Apple, not Pineapple). One match loads it; several show
  "Did you mean …" with up to 8 names; none shows "No company found". A ticker match always beats a
  name match, so typing "ford" opens FORD (Forward Industries), not Ford Motor (F); both appear in the
  suggestions while typing.
- **2026-11-11 · decision:** three separate error messages, each its own exception type: unknown ticker;
  no financial statements (the SEC answers 404 for SPY, or the data has no `us-gaap`/`ifrs-full`
  section) — "probably an ETF or a fund"; and no annual report (data exists but no 10-K rows) —
  "listed recently, or a foreign company that files a 20-F". The last one gets reworded in task 3.
- **2026-11-11 · decision:** popular examples appear when the box is empty: six buttons on the company
  page (AAPL, MSFT, NVDA, KO, WMT, TSLA) and three on compare (AAPL vs MSFT vs NVDA, KO vs PEP,
  WMT vs COST vs TGT). `display.parse_tickers` was deleted (nothing uses it now).
- **2026-11-11 · decision (tests):** Streamlit's test harness refuses a selectbox value that isn't a
  listed option, so the page tests replace the one method that builds the message sent to the app.
  **Why:** otherwise typed tickers and names couldn't be tested through the page at all. It depends on
  a private Streamlit attribute (`Selectbox._widget_state`), so a Streamlit upgrade could break these
  tests (not the app).
- **2026-11-11 · outcome:** 174 tests pass. Real browser: "coca" suggests KO first; brk.b and "brk b"
  open Berkshire; SPY gives the fund message; TSM gives the no-annual-report message; "zzzzqq" gives
  not found; "apple" asks AAPL or APLE; the KO example button opens Coca-Cola.
- **Suggested for `LEARNING.md`:** *Normalization* = turning different spellings of the same thing
  (BRK.B, brk b) into one standard form before looking it up. *Autocomplete* = suggestions that narrow
  as you type.

## S3 Task 3 — Foreign filers (IFRS, 20-F, 40-F)

- **2026-11-12 · decision:** SPEC.md scope is now "companies filing with the SEC, US GAAP or IFRS";
  "EU companies" in the out-of-scope list became "companies that don't file with the SEC" and "currency
  conversion".
- **2026-11-12 · decision:** annual forms are 10-K, 10-K/A, 20-F, 20-F/A and 40-F, exactly as asked.
  **Not added:** 40-F/A (not in the request; one word in `parse.ANNUAL_FORMS` if wanted).
- **2026-11-12 · decision:** the IFRS tags are a separate table, `schema.IFRS_TAGS`, keyed by line item
  name, covering all 23 items (temporary equity is empty: IFRS has no such line) plus three helper
  items. **Why:** one readable block, and the 23 existing item definitions stay untouched.
  **Rejected:** a new field on every `LineItem`.
- **2026-11-12 · decision:** the reporting currency is the currency most annual total-assets facts are
  in. **Why:** TSMC and Toyota also give a US dollar translation of the latest year, so "any currency
  present" would pick wrongly; the home currency always has more facts. It is stored in each row's
  existing `unit` column ("EUR", "EUR/shares"), so the database needed no new column.
- **2026-11-12 · decision:** each fiscal year uses one taxonomy only: that of the latest filing
  reporting its total assets. **Why:** Toyota's FY2019–20 exist under both, and mixing them added US
  GAAP temporary equity to an IFRS balance sheet, failing the balance check by JPY 500–590bn. After the
  change both years balance.
- **2026-11-12 · decision:** non-dollar amounts read "EUR 1,234M" (code, then number); dollars stay
  "$1,234M". **Rejected:** currency symbols (€, ¥, NT$): a table to maintain, and ¥ is ambiguous.
- **2026-11-12 · decision:** for companies that don't report in dollars, P/E, P/B, EV/EBIT and FCF
  yield are unavailable with the reason; market cap (in dollars, from Yahoo) still shows. **Why:**
  dividing a dollar market cap by euro or yen profit gives a meaningless number, and conversion was
  explicitly not wanted yet. The company page says which currency it's in; the compare page notes when
  currencies differ and labels the over-time chart "millions, each in its own currency".
- **2026-11-12 · decision (search, found while testing this task):** on the compare page, typing "AAPL"
  and pressing Enter chose Streamlit's "Select 632 matches" entry, i.e. four look-alike companies, and
  "ko" chose Koss before Coca-Cola. Fixed by switching that box off "select all" and to plain substring
  matching, which keeps the SEC's largest-first order. **Still imperfect:** one- and two-letter tickers
  (F, T, MA) on the compare page offer a bigger company containing those letters first; pick from the
  list. The company page isn't affected (typed text is resolved by our own exact-ticker rule).
- **2026-11-12 · two small tag changes:** IFRS interest expense reads `InterestExpense`, then
  `FinanceCosts` (not `InterestExpenseOnBorrowings`, which at TSMC is 1% of the real figure); and US
  GAAP short-term investments gained `AvailableForSaleSecuritiesDebtSecuritiesCurrent` (ASML). The
  second also fills Apple FY2009–10 ($18,201M and $14,359M, which match its 10-K); nothing else
  changed across AAPL, KO, TSLA, NVDA, JPM, GS and BRK-B (2,301 rows compared before and after).
- **2026-11-12 · outcome:** 187 tests pass. Real data, per company:

  | Company | Reports | Years | Latest-year metrics | Gaps |
  |---|---|---|---|---|
  | TSM | IFRS, TWD | 2015–2024 | 19 of 19 (gross margin 56.1%, net margin 40.0%, ROE 30.2%, all match its annual report) | **Debt leaves out bonds**, so debt/equity shows 0.02× (about 0.25× is right) and ROIC is overstated: #26. All years balance. |
  | ASML | US GAAP, EUR | 2007–2025 | 19 of 19 (gross margin 52.8%, net margin 29.4%) | FY2015–17 miss the balance check by EUR 66–152M (0.4–0.9% of assets); not investigated. |
  | SAP | IFRS, EUR | 2015–2025 | 19 of 19 (gross margin 72.9%, net margin 19.5%) | No inventory (none exists; treated as 0). Capital expenditure includes intangibles. Interest expense is `FinanceCosts` before FY2023. FY2017–18 miss the balance check by EUR 58–71M. |
  | TM | US GAAP to FY2020, IFRS after, JPY | FY2008–FY2025 | 16 of 19 | **No cost of revenue or capital expenditure since FY2021** (Toyota's own tags, not in the SEC data), so gross margin, free cash flow and FCF margin are unavailable: #27. Diluted share count missing FY2021–22. All years balance. |

  All four: valuation ratios unavailable (no conversion). Checked in a real browser: TSM and TM pages
  render with the currency note; AAPL + SAP + TM on compare shows the currency note.
  **Not checked:** a 40-F filer on real data (task 4 includes some).
- **Suggested for `LEARNING.md`:** *IFRS* = the accounting rules used in most countries outside the US
  (the US uses *US GAAP*). *20-F* = the annual report a foreign company files with the SEC, like a
  10-K. *Reporting currency* = the currency a company's statements are written in. *ADR* = a US-listed
  share that stands for shares of a foreign company.

## S3 Task 4 — Stress test on 30 companies

- **2026-11-12 · decision:** the 30 tickers, by group: mega caps MSFT, GOOGL, AMZN, META; small and mid
  caps PLOW, CALM, CROX; retail WMT, COST, TGT, HD; energy XOM, CVX, OXY; pharma PFE, LLY, MRNA;
  utilities NEE, DUK; REITs O, PLD, AMT; foreign filers NVO (IFRS, DKK), SHEL (IFRS, USD), CNQ (40-F,
  CAD), BABA (US GAAP, CNY), SONY (JPY); recent IPOs RDDT (2024), CRWV (2025); loss-making RIVN (MRNA
  and CRWV also lose money).
- **2026-11-12 · decision:** the test is a committed script, `scripts/coverage.py`, that writes
  `docs/COVERAGE.md`. **Why:** it can be rerun after any tag change to see whether another company got
  worse. It needs the network, so it isn't part of `pytest`. The "what the gaps have in common" section
  is hand-written text kept in the script.
- **2026-11-12 · fixed directly (5):**
  1. Revenue for utilities: `RegulatedAndUnregulatedOperatingRevenue`, then
     `RevenueFromContractWithCustomerIncludingAssessedTax`, added after the existing tags.
  2. Interest expense: `InterestAndDebtExpense` (OXY).
  3. Capital expenditure: `PaymentsToAcquireOtherPropertyPlantAndEquipment` (LLY).
  4. Cash: `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`, but only for years with no
     plain cash figure, labelled "includes restricted cash" (TGT, CVX, PLOW). **Why not a plain fallback
     tag:** later filings repeat old year-ends under this tag, and "latest filing wins" would have
     replaced Apple's plain cash with the larger total.
  5. Shareholders' equity: where the parent's share isn't tagged, total equity less minority interest,
     labelled as calculated, only for years that have a balance sheet (NVO, CNQ, RIVN). This is a
     small rule, not a tag; it's here because 3 of 30 companies had no ROE without it.
- **2026-11-12 · effect of the fixes:** NEE 9 → 15 metrics, DUK 9 → 16, CNQ 9 → 13, NVO 15 → 19,
  RIVN 12 → 15, LLY 14 → 16, TGT 18 → 19, PLOW 17 → 18. On the seven reference companies (AAPL, KO,
  TSLA, NVDA, JPM, GS, BRK-B) the only change is new cash rows for JPM and BRK-B, labelled as including
  restricted cash.
- **2026-11-12 · filed, not fixed:** #29 no operating income subtotal (7 companies); #30 restated older
  years fail the balance check (9 companies, MSFT FY2016 by $11bn); #31 REITs; #32 ExxonMobil has only
  quarterly data in the SEC feed, so it can't be loaded (the error message now says so); #33 cost of
  revenue and capex at energy companies and utilities. Evidence added to #1 (items absent after being
  reported). **Why not fixed:** each needs a new rule or a per-industry tag list, not a fallback tag.
- **2026-11-12 · outcome:** 190 tests pass. 29 of 30 load; 8 have all 19 metrics for the latest year;
  20 of 29 balance in every stored year (all failures are in older years, except CRWV FY2024).
  **Not checked:** the values themselves for these 30, beyond spot checks of the fixed items (DUK
  revenue $32,237M and NEE $27,412M match the tagged totals). The table records what is missing, not
  whether what's present is right.

## S4 Task 1 — Compare page: an exact ticker always wins

- **2026-11-12 · decision:** the compare box now matches from the start of each entry (Streamlit's
  `filter_mode="prefix"`) and lists the shortest tickers first. Enter picks the first match, and the
  first entry starting with "F" is now "F — Ford": no shorter ticker exists, and FAST, FE and the rest
  come after it. **Why this and not a smarter order:** the box filters in the browser and tells the app
  only what was picked, not what was typed, so the app can't correct a wrong pick afterwards. With
  substring matching no order works at all: "T — AT&T" contains "a" and "A — Agilent Technologies"
  contains "t", so one of them always loses.
- **2026-11-12 · decision:** every company is in the compare list twice, once ticker first ("KO — COCA
  COLA CO") and once name first ("COCA COLA CO — KO"). **Why:** matching from the start would otherwise
  end name suggestions. **Trade-offs:** (1) a name is now suggested only from its first word: "Coca"
  suggests Coca-Cola, "Hathaway" suggests nothing, though typing it and pressing Enter still gets the
  "did you mean BRK-B, BRK-A" message; (2) within one ticker length the order is still largest first,
  but "AAP" + Enter now picks Advance Auto Parts (ticker AAP), not Apple, which is what "exact ticker
  wins" means; (3) the list is 20,807 entries instead of 10,405; it still suggests within a second.
- **2026-11-12 · not changed:** the company page. It takes typed text as typed and already resolves an
  exact ticker first.
- **2026-11-12 · checked:** in a real browser F → Ford, ma → Mastercard, T → AT&T, brk.b → BRK-B,
  "Coca" → Coca-Cola, "apple inc" → Apple. A script over all 10,405 SEC tickers found 0 where the first
  match is a different company. 208 tests pass (190 before); the new ones cover one- and two-letter
  tickers that also appear inside longer entries (F/FAST, MA/MAR, T/TM, M/MSFT, W/Wayfair).

## S4 Task 2 — TSMC debt: bonds reported apart from borrowings (#26)

- **2026-11-12 · departed from the instruction, on evidence:** you asked for bonds to be added to debt
  for every IFRS filer, because double-counting is a US GAAP risk. It is an IFRS risk too: Novo Nordisk
  (IFRS, already in the stress test) reports long-term borrowings of DKK 118.9bn **and** tags the
  DKK 111.4bn of bonds inside that figure. Adding bonds for every IFRS filer would have shown Novo with
  DKK 230bn of long-term debt, nearly double the truth.
- **2026-11-12 · decision:** bonds are added, for IFRS filers only, when they are larger than the
  borrowings figure for that year (or when no borrowings figure exists). **Why:** a part can't be bigger
  than its whole, so bonds larger than borrowings can't already be inside it. TSMC: bonds TWD 926.6bn
  against borrowings of 31.8bn, added. Novo: 111.4bn against 118.9bn, left alone. The row is labelled
  "borrowings + bonds issued, reported apart from borrowings". The same rule runs on short-term debt.
  **Known gap:** a company whose separate bonds are *smaller* than its bank loans still has them left
  out (debt understated, as before); none of the 11 IFRS companies checked has that shape.
  **Rejected:** comparing with the `Borrowings` total; TSMC doesn't report one.
- **2026-11-12 · result:** TSM FY2024 long-term debt TWD 958.4bn (was 31.8bn); debt/equity 0.24×
  (was 0.02×); FY2020–23: 0.19×, 0.34×, 0.30×, 0.27×. ROIC FY2024 36%. TSMC's short-term debt didn't
  change: its "current portion of long-term borrowings" (59.9bn) already includes the current bonds
  (57.1bn). FY2016–19 gain long-term debt rows from bonds alone (no borrowings were tagged then).
- **2026-11-12 · checked:** every parsed row for 40 companies (the 7 reference companies, TSM, ASML,
  SAP, TM and the 29 that load from the stress test) was printed before and after and compared: 12,179
  rows, and the only differences are TSM's long-term debt. US GAAP companies can't change: the rule
  reads IFRS tags only. 211 tests pass, including both shapes (TSMC's and Novo's).
  **Not checked:** TSMC's figure against its printed annual report; 958.4bn is the sum of its two tagged
  lines.

## S4 Task 3 — Valuation ratios for foreign filers (market cap converted)

- **2026-11-12 · scope:** `SPEC.md` listed currency conversion as out of scope for v1. You asked for it,
  so I built it and changed the spec in the same PR: market cap is converted for the valuation ratios;
  the financial statements still aren't converted (that stays out of scope).
- **2026-11-12 · decision:** the rate comes from Yahoo's `TWD=X`-style symbol for every currency
  (`EUR=X`, `JPY=X`, `DKK=X`…), which is "how much of the currency one US dollar buys". **Why not
  `EURUSD=X` for euros:** that one is quoted the other way round (dollars per euro), so using it would
  need a table of which currencies are inverted. `EUR=X` gives the same rate with one rule for all.
  Checked live: TWD 32.94, EUR 0.9015, JPY 159.70, DKK 6.74, CAD 1.43, CNY 6.67.
- **2026-11-12 · decision:** market cap in dollars × the rate = market cap in the statements' currency,
  and the four ratios use that. The Market cap card itself stays in dollars, as Yahoo reports it. Each
  ratio's "Formula and meaning" lists the dollar market cap, the rate and the converted market cap.
  The line under "Valuation at today's price" shows the rate and its date, e.g. "Market cap is converted
  into TWD at 1 USD = 32.9450 TWD (Yahoo Finance, Nov 12, 2026)". The date is the day the rate was
  fetched; like the share price it is reused for 15 minutes.
- **2026-11-12 · failure:** if the rate lookup fails, the four ratios read "unavailable" with the reason,
  the note says "Exchange rate unavailable: …", and market cap still shows. Tested.
- **2026-11-12 · result (live, 2026-11-12):**

  | | P/E | P/B | EV/EBIT | FCF yield |
  |---|---|---|---|---|
  | TSM (FY2024) | 60.97× | 16.64× | 52.54× | 1.2% |
  | ASML (FY2025) | 55.48× | 27.18× | 46.38× | 2.1% |
  | SAP (FY2025) | 34.02× | 5.46× | 24.95× | 3.5% |
  | TM (FY2025) | 8.41× | 1.12× | 13.12× | unavailable |

  Toyota's FCF yield is unavailable because its capital expenditure isn't found (#27), not because of
  the conversion.
- **2026-11-12 · found, filed as 37:** TSMC's ratios are against FY2024, because the SEC's data
  feed has none of the statements from its FY2025 report (filed 2026-04-16; only 2 facts arrived). So
  its P/E of 61× is higher than finance sites show. Same family as ExxonMobil (#32). Not fixed.
- **2026-11-12 · also in this PR:** the README limitation "TSMC's debt leaves out its bonds" is removed;
  it belonged to task 2 and I noticed it after this branch had started.
- **2026-11-12 · checked:** company page for TSM and TM and the compare page (AAPL, SAP, TSM) in a real
  browser, no errors. 219 tests pass; yfinance is mocked in all of them. **Not checked:** the ratios
  against another source; Yahoo's market cap for the US-listed shares (ADRs) is taken as given.
- **LEARNING.md suggestion:** "Exchange rate pair": `TWD=X` means "Taiwan dollars per one US dollar".
  To compare a dollar market cap with profits in Taiwan dollars, both must be in the same currency first.

## S4 Task 4 — `.devcontainer` removed

- **2026-11-12 · decision:** deleted `.devcontainer/devcontainer.json` rather than fixing it.
  **What it was:** settings for GitHub Codespaces (an editor in the browser), added on Nov 11 by
  Streamlit's "edit in Codespaces" button, not by this project. It asked for Python 3.11 and a
  `requirements.txt`, neither of which this project uses, so a Codespace opened from it couldn't start
  the app.
  **Why delete:** (1) Streamlit Community Cloud doesn't read it: the live app is built from
  `pyproject.toml`, `uv.lock` and `streamlit_app.py`, so nothing changes there. (2) Nothing in the repo
  refers to it. (3) A fixed version couldn't be tested from here, since that needs a Codespace on your
  GitHub account, and it would also need `SEC_USER_AGENT` set as a Codespaces secret. An untested
  config that looks supported is worse than none. (4) The README already has two tested ways to run the
  app: `uv` and Docker.
  **If you want Codespaces later:** it is about ten lines (Python 3.12 image, `uv sync` after create,
  `uv run finance-analyzer` on attach, port 8501) plus the secret; best written when you can open one
  and watch it start.
- **2026-11-12 · checked:** 219 tests pass; no file mentions the folder. **Not checked:** the live app
  after this merges (it shouldn't notice).

## S4 Task 5 — 40-F/A accepted

- **2026-11-12 · done:** `40-F/A` (an amended Canadian annual report) is now an accepted annual form,
  beside 10-K/A and 20-F/A. One word in `parse.ANNUAL_FORMS` and one more case in the form test.
  As with the other amendments, "latest filing wins" means an amendment's figures replace the original's.
- **2026-11-12 · checked:** 220 tests pass. All 40 downloaded companies parse to exactly the same rows
  as before. **Not checked on real data:** none of those 40 has a 40-F/A (Canadian Natural Resources,
  the one 40-F filer, has never amended), so this is covered by the unit test only.

## S4 Task 6 — Release notes for v1.1.0

- **2026-11-12 · done:** `CHANGELOG.md` now has two versions. **1.0.0** absorbed what was under
  "Unreleased" (search, foreign filers, the stress test, docs), as you defined it: everything up to
  session 3. Its data, screens, test count (190) and known limits were updated to match, and its date
  is 2026-11-12, the day session 3 was merged. **1.1.0** lists this session: added (foreign valuation,
  40-F/A), fixed (compare search, TSMC debt), removed (`.devcontainer`), known limits (#37, #27,
  #29–#33).
- **2026-11-12 · decision:** the 1.1.0 heading reads "not released yet (notes prepared 2026-11-12)" and
  `pyproject.toml` stays at 1.0.0. **Why:** you asked for notes to be prepared, not for a release, and
  a version number that is ahead of the last release is harder to notice than a heading that says so.
  **To release:** merge the six PRs, put the date in the heading, set `version = "1.1.0"` in
  `pyproject.toml`, run `uv lock`, then tag. No tag exists for 1.0.0 either.
- **2026-11-12 · checked:** every claim in the 1.1.0 notes against the S4 task entries above.

## S5 Task 1 — Red-flag scores

- **2026-11-12 · scope:** `SPEC.md` listed red-flag scores as out of scope for v1. You asked for them, so
  I built them and moved the line into the spec's metrics list in the same PR.
- **2026-11-12 · decision (the one to review): Altman Z is the Z″ version, not the classic 1968 Z.**
  The classic score needs the market value of equity, and the app only knows today's share price, so it
  couldn't be calculated "per year" as you asked. Z″ (Altman's 1995 version) swaps market value for the
  equity on the balance sheet and drops the sales term, so every year works and no price is needed.
  Its cut-offs are 2.6 and 1.1, not 2.99 and 1.81, and its numbers won't match finance sites that show
  the classic score. The card is labelled "Altman Z″" and the learning text says so.
  **Rejected:** the classic Z for the latest year only (one number, no history, and unavailable whenever
  Yahoo is); fetching a share price for every past year-end (a new data source and many more requests).
- **2026-11-12 · decision:** five line items were added to the schema because the scores need them:
  SG&A, receivables, property/plant/equipment, retained earnings, and depreciation & amortization, each
  with US GAAP and IFRS tags. SG&A is the reported total, or selling/marketing + general/administrative
  where a company reports those separately (Microsoft, Alphabet, TSMC), labelled as calculated. The
  company page's line-item table shows them too. Checked on 40 companies: every existing row is
  unchanged; only the new rows were added.
- **2026-11-12 · the four formulas:**
  - **Altman Z″** = 6.56 × working capital/assets + 3.26 × retained earnings/assets + 6.72 × operating
    income/assets + 1.05 × total equity/total liabilities.
  - **Piotroski F**: his nine tests, with return on assets, cash flow and turnover measured against
    opening assets as in the paper, so it needs two prior years. Two small departures, both in the
    learning text: an unchanged debt ratio passes (otherwise a company with no debt would lose a point),
    and the diluted average share count stands in for shares outstanding, which the schema doesn't hold.
  - **Beneish M**: the eight-variable model. Net income is used for "income from continuing operations",
    and depreciation includes amortization where the company reports them together.
  - **Accruals ratio** = (net income − operating cash flow) ÷ average total assets. **Rejected:** Sloan's
    fuller version, which also subtracts investing cash flow: that needs another line item.
- **2026-11-12 · decision:** a score with any input missing is "unavailable" with the reason; it is never
  calculated from a partial set (a Piotroski score out of 7 would read like a bad score out of 9).
- **2026-11-12 · where they show:** a "Red flags" section on the company page: four cards for the latest
  year with the value, what it says ("Safe zone", "⚠ Flag: above −1.78"…), the formula with every input,
  and learning text; then a table for the last five years. Banks, brokers and insurers get a line saying
  the scores don't apply. **Not added:** to the compare page or the Excel export (not asked).
- **2026-11-12 · result on 40 real companies (latest year):** Altman Z″ available for 28, Piotroski F
  for 24, Beneish M for 24, accruals ratio for all 40. The gaps follow the known data issues: no
  operating income subtotal (#29: CVX, PFE, LLY…), no cost of revenue (#27, #33: Toyota, utilities,
  energy), REITs and banks (no current assets). Flags raised: NVIDIA (Beneish −1.15 and accruals 10.9%,
  typical of very fast growth), CoreWeave (Beneish 0.10, Z″ −1.30), Rivian (Z″ −4.90), utilities and
  American Tower in the distress zone, which is the known weakness of Z-scores for regulated,
  debt-funded businesses.
- **2026-11-12 · tests:** `tests/test_red_flags.py`, with Apple FY2026 and Coca-Cola FY2025 worked by
  hand in the comments: Z″ 3.2024 and 4.5036; F 9 and 7 (Coca-Cola fails tests 4 and 9); M −2.5158 and
  −2.3499 with all eight indexes; accruals −3.38% and 5.55%. I did the arithmetic in a separate script
  that doesn't import the app. 241 tests pass (220 before).
  **Not checked:** the scores against another source (and Z″ wouldn't match one anyway).
- **2026-11-12 · small changes alongside:** `scripts/coverage.py` still counts the 19 ratios, so
  `docs/COVERAGE.md` stays comparable; it wasn't rerun, and when it is, the five new line items will
  appear in its "missing items" columns.
- **LEARNING.md suggestion:** "Accrual": profit counts a sale when it's made, cash flow when the money
  arrives. The gap between the two is accruals; a big gap means profit is ahead of cash.

## S5 Task 2 — Peer suggestions

- **2026-11-12 · decision (the one to review): peers come from a file shipped with the app,
  `src/finance_analyzer/peers.json`, not from live SEC calls.** It lists 4,239 companies as
  ticker → [SIC code, revenue in US dollars for fiscal 2025] and is 99 KB.
  **Why:** the SEC has no "every company with this industry code" lookup that also gives revenue.
  Doing it live would mean paging through the SEC's company browser and then downloading each
  candidate's full facts (several MB each) just to rank them. With the file, suggestions are instant
  and need no network. **The cost:** it goes stale. Industry codes rarely change, but revenue is a year
  old by the time the next annual reports arrive, and a company that listed after the file was built
  isn't suggested. `scripts/build_peers.py` rebuilds it (about a minute, 280 MB of downloads); run it
  about once a year. **Rejected:** peers only from companies already in the app's database (far too few).
- **2026-11-12 · where the file's data comes from:** SIC codes from the SEC's four latest quarterly
  "Financial Statement Data Sets"; revenue from the SEC "frames" API, which returns one fact for every
  company in a single call, tried in the schema's revenue tag order. One ticker per company (the first
  in the SEC's list), so Alphabet appears once.
- **2026-11-12 · the rule:** same 4-digit SIC code first, closest revenue first; if that gives fewer
  than 5, topped up from the same 3-digit group (marked "wider industry group" in the button's
  tooltip). "Closest" is by ratio, so half the size and double the size count as equally far.
  A company never gets itself or its own other share class (GOOG/GOOGL).
- **2026-11-12 · decision, foreign filers:** a company that reports in another currency (TSMC, SAP) has
  no dollar revenue in the file, so closeness can't be measured; it gets the five **largest** companies
  with its code instead, and the caption says "largest first". Such companies are also rarely suggested
  *as* peers (only when they tag a dollar figure, as Alibaba does).
- **2026-11-12 · one click:** each peer is a button showing ticker and revenue; clicking opens the
  compare page with the company and that peer. A sixth button, "Compare X with the first 3", fills all
  four compare slots. (Compare takes at most 4 companies, so "company + all 5 peers" isn't possible.)
- **2026-11-12 · bad SEC data found and handled:** Tigo Energy (TYGO) tagged its FY2025 revenue twice,
  once as $103.5M and once as $103.5bn, which made it NVIDIA's "closest peer". The build script now
  takes the smaller figure when two revenue tags differ by exactly 1,000× or 1,000,000×. **Not fixed:**
  the app's own company page for TYGO would still show the $103.5bn figure; it's one filer's error and
  I didn't file an issue for it.
- **2026-11-12 · examples (live file):** KO → PEP, KDP, STZ, PRMB, BF-B. WMT → COST, TGT, DG, BJ, DLTR.
  NVDA → AVGO, INTC, MU, AMD, AMAT. JPM → BAC, C, USB, PNC, COF. AAPL → DELL, SMCI, then three tiny
  companies: Apple's SIC code (3571, electronic computers) simply has few members, and SIC codes are
  coarse (Microsoft is "prepackaged software", Alphabet "computer programming services").
- **2026-11-12 · checked:** in a real browser, KO → click PEP and TSM → "first 3" both open the compare
  page loaded. 248 tests pass (241 before). **Not checked:** `scripts/build_peers.py` has no automated
  test (it is all downloads); ExxonMobil and other companies with no revenue in the frames feed are
  missing from the file, so they are never suggested as peers.
- **`SPEC.md`:** peer suggestions added under Screens.
- **LEARNING.md suggestion:** "SIC code": a 4-digit industry number the SEC gives every filer. The first
  3 digits are a wider group, the first 2 wider still (20 = food, 2080 = beverages).

## S5 Task 3 — Quarterly figures and the trailing twelve months (TTM)

- **2026-11-12 · scope:** the app was annual-only (README: "no quarters"). You asked for this, so it's
  built and `SPEC.md`/README are updated in the same PR.
- **2026-11-12 · how quarters are built:** from 10-Q facts. Q1 is as reported. Q2 and Q3 are as reported
  where the company gives the quarter on its own, otherwise the year-so-far figure minus the quarters
  before (cash flow statements only ever give the year so far). **Q4 = full year − first nine months**,
  always, as you specified. TTM = the last four quarters; if any of the four is missing there is no TTM
  figure for that item, never a three-quarter total.
- **2026-11-12 · decision (the design): TTM figures are fed back through the existing annual rules.**
  The SEC facts are rewritten as if a fiscal year ended at the latest quarter end (flows become TTM
  sums, balance sheet items are those reported on that date), then go through the same code as annual
  data. **Why:** every tag priority and calculated item (short-term debt from parts, SG&A, cash,
  bonds…) and every metric, including the red-flag scores, works on TTM with no second copy of the
  rules. The same is done for the same quarter end in each earlier year, so averages, growth rates and
  the five-year trends compare like with like (twelve months to Sep 2026 against twelve months to
  Sep 2025).
- **2026-11-12 · decision:** TTM rows are built on demand from the SEC download and are **not saved in
  the database**, which still holds fiscal years only. **Why:** no change to the table, and nothing to
  keep in sync. Cost: about 0.1 s per company, cached for a day.
- **2026-11-12 · what the toggle does:** "Period: Fiscal years / Trailing 12 months" on the company
  page. TTM swaps the line items, metric cards, valuation (P/E on TTM profit, which is what finance
  sites show), trends, DuPont and red flags; columns read "12m to Sep 2026". An expander lists the last
  eight single quarters for seven main items, with calculated values starred. **Stay annual:** the Excel
  export, data checks, peers and the compare page.
- **2026-11-12 · foreign filers:** 20-F and 40-F companies file no quarterly data with the SEC (TSM,
  ASML, SAP, TM, NVO, SHEL, CNQ, BABA, SONY), so the toggle shows a message and stays on fiscal years.
- **2026-11-12 · three real-data problems found and fixed while checking 40 companies:**
  1. Amazon's 10-Qs also report rolling twelve-month figures; they were mistaken for fiscal years.
     Only annual reports mark a fiscal year end now.
  2. Costco's quarters are 12 weeks (then 16), outside my first day ranges; widened.
  3. Stock splits: the annual code dates a split to the first *annual* report after it, but 10-Qs in
     between are already on the new basis, so NVIDIA's share count came out 10× too big for one year.
     Splits are now dated from quarterly reports for TTM, and a split seen in several later reports is
     counted once. After the fix, TTM EPS equals TTM profit ÷ shares to within a few cents for NVDA,
     AAPL, TSLA, GOOGL, AMZN and WMT in every year.
- **2026-11-12 · known limits:**
  - TTM EPS is the sum of four quarterly EPS figures, so it can differ from the annual EPS by a cent or
    two (Apple: 8.97 against 8.98 for the same twelve months). The share count is the latest quarter's.
  - Reasons from the engine still say "FY2026" in TTM view; a line on the page explains how to read it.
  - Banks lose more in TTM: JPMorgan tags annual revenue differently from quarterly revenue, so its TTM
    revenue is missing (6 metrics against 11 annual). Of the 31 companies with quarterly data, 20 have
    the same number of metrics in both views; 4 have one or two more in TTM, 7 have fewer (JPM, PLOW,
    CVX: long-term debt tagged differently in 10-Qs; META, TGT, COST, MRNA, DUK, CRWV by one or two).
  - Two splits within 400 days of each other would be read as one.
- **2026-11-12 · checked:** KO and TSM in a real browser; KO's TTM revenue $51,054M against FY2025
  $47,941M, P/E 28.7×. 260 tests pass (248 before), including hand-made filings for each quarter shape.
  **Not checked:** TTM figures against another source.
- **LEARNING.md suggestion:** "TTM (trailing twelve months)": the last four quarters added together, so
  the figure is always a full year but as fresh as the latest quarterly report.

## S5 Task 4 — Industry benchmarks

- **2026-11-12 · what it does:** each metric card on the company page gets a line "Industry median: 4.2%
  (3 companies)": the middle value of that metric across the companies saved in the app's database whose
  SIC code starts with the same two digits, each taken for its latest fiscal year. A caption above the
  cards names the companies in the sample and says it's a small sample, not the whole industry.
- **2026-11-12 · decision:** a median is shown only when at least 3 companies have a value for that
  metric (the company itself counts). **Why:** with one or two companies the "median" is just one
  company's number, or the average of two, dressed up as an industry figure. Below 3 the page says how
  many are loaded so far and which.
- **2026-11-12 · decision:** no median for free cash flow (an amount: it depends on size and currency),
  for the DuPont tile (it repeats ROE) or for the five valuation ratios (they'd need a share price for
  every company in the group on each page view). The red-flag scores do get one.
- **2026-11-12 · decision:** a stored company's SIC code is read from `peers.json` when it's there (no
  download), otherwise from the SEC company info already cached on disk when the company was loaded.
- **2026-11-12 · limits worth knowing:**
  - The sample is whatever has been loaded, so it changes as people use the app and differs between
    your computer and the live site. Task 6's pre-load gives the live site a fixed starting set.
  - Two-digit SIC groups are wide, as specified: group 35 puts Apple with ASML and Douglas Dynamics
    (snow ploughs); group 73 puts Microsoft with Mastercard and Reddit.
  - Medians are remembered for a day per company viewed, so a company loaded later joins the figure on
    other companies' pages only after that, or after "Refresh data".
  - In the trailing-twelve-months view the company's own figures are TTM while the medians stay on
    fiscal years.
  - Ratios mix currencies and year-ends freely; that's fine for ratios.
- **2026-11-12 · checked:** Walmart in a real browser (group 53: COST, TGT, WMT). In my local database 8
  groups have 3 or more companies. 262 tests pass (260 before). **Not checked:** speed with hundreds of
  stored companies; each first view recalculates the metrics of every company in the group.
- **`SPEC.md`:** benchmark line added under Screens.
- **LEARNING.md suggestion:** "Median": line the values up in order and take the middle one. Unlike an
  average, one extreme company can't drag it.

## S5 Task 5 — Shareable links

- **2026-11-12 · what it does:** `?ticker=AAPL` opens the company page on that company and
  `?compare=AAPL,KO` opens the compare page with those companies. It also works the other way: once a
  company or comparison is on screen the browser's address is updated to match, so "copy the address"
  is the share button. Examples: `https://datadough.streamlit.app/?ticker=AAPL`,
  `https://datadough.streamlit.app/?compare=AAPL,KO`.
- **2026-11-12 · decision:** a link is read **once**, when the page is first opened. After that the
  search box decides, and the address follows it. **Why:** otherwise the link and the box would fight:
  picking another company would be overridden by the old `?ticker=` on the next refresh of the page.
- **2026-11-12 · decision:** text from a link is treated exactly like typed text, so `?ticker=brk.b`
  finds BRK-B and a wrong ticker gets the usual "No company found" message. It is cut to 40 characters
  first, and a compare link is cut to the first 4 different companies (the box's limit). **Why:** a link
  can come from anyone, so it gets no more trust than the keyboard.
- **2026-11-12 · decision:** `?compare=` works at the site's root (as in your example) as well as on
  `/compare_page`; at the root the app moves to the compare page itself.
- **2026-11-12 · not in the link:** the Period toggle (fiscal years / TTM) and the compare page's chart
  metric. A link always opens on fiscal years. Streamlit also clears the address when you switch page
  from the sidebar, which is right here: each page then writes its own.
- **2026-11-12 · checked:** in a real browser: `?ticker=KO`, `?ticker=brk.b` (address becomes
  `?ticker=BRK-B`), `?compare=AAPL,KO`, `/compare_page?compare=WMT,COST,TGT`, and the address changing
  to `?ticker=MSFT` after picking Microsoft. 266 tests pass (262 before). **Not checked:** on the live
  site, where the address bar belongs to Streamlit Cloud's wrapper page; Streamlit documents query
  parameters as working there, but I couldn't confirm it from here.
- **README and `SPEC.md`:** one line each.

## S5 Task 6 — Pre-load on the hosted app, and first-load time

- **2026-11-12 · what it does:** `streamlit_app.py` (the file Streamlit Cloud runs) now starts a
  background job, once per server start, that loads every stress-test company not yet in the database
  and fetches its company info. Pages never wait for it. `uv run finance-analyzer` and Docker don't
  pre-load. The 30-ticker list moved to `src/finance_analyzer/preload.py`; `scripts/coverage.py` reads
  it from there.
- **2026-11-12 · two safety changes it needed:** downloads are written under a temporary name and then
  renamed, so a page can't read a half-written file; saving a company takes a lock, so a page view and
  the pre-load can't write the same company at once.
- **2026-11-12 · measured (my machine, empty data folder, real SEC downloads, one run each):**

  | | no pre-load | pre-loaded |
  |---|---|---|
  | MSFT | 2.3 s | 1.6 s |
  | WMT | 1.9 s | 0.9 s |
  | PFE | 2.0 s | 1.0 s |
  | NEE | 2.0 s | 0.9 s |
  | RIVN | 1.5 s | 1.0 s |

  Time is from pressing Enter to the Data checks section showing. The pre-load itself took 39 s for 29
  companies (ExxonMobil fails as before, #32) and left 98 MB on disk. KO, not pre-loaded, took 2.0 s on
  the pre-loaded server.
- **2026-11-12 · honest reading:** the gain is about one second here, because my connection downloads a
  company in under a second. What remains after pre-loading is parsing and drawing the page.
  **Not measured:** the live site, where downloads are likely slower and the gain larger; memory use on
  Streamlit Cloud's 1 GB limit while 30 files are parsed one after another; a single run per figure, so
  differences of a few tenths mean nothing.
- **2026-11-12 · checked:** 271 tests pass, including that the hosted entry point starts the pre-load
  once and the local one never does.

## S6 Task 1 — Pre-load opt-in: skipped

- **2026-11-13 · skipped, as the queue allowed:** there is no sign of memory problems from the
  pre-load. **Evidence:**
  1. I couldn't look at the live app: https://datadough.streamlit.app now redirects to a Streamlit
     login page, so it is set to private (or viewer-only) and its logs need your account.
  2. Locally, on an empty data folder, a full pre-load of the 30 companies peaked at **201 MB**, against
     **176 MB** for just starting the app: the pre-load adds about 25 MB, because it loads one company
     at a time and keeps nothing in memory afterwards.
  3. Streamlit's documentation gives Community Cloud apps 690 MB to 2.7 GB of memory ("as of February
     2024"; https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app). An app over
     its limit shows "Oh no."
- **2026-11-13 · seen during the measurement:** PLOW failed once with a read timeout from the SEC (the
  30-second limit) and was simply skipped, as designed; the next view of PLOW downloads it again.
- **If you do see "Oh no." or "gone over its resource limits"** on the live app: tell me, and the opt-in
  switch is a two-line change in `streamlit_app.py`.
- **Worth knowing:** if the private setting wasn't intended, anyone following the README's "Try it"
  button currently lands on a login page. Share settings are under ⋮ → Settings → Sharing at
  share.streamlit.io.

## S6 Task 2 — Coverage rerun

- **2026-11-13 · done:** `scripts/coverage.py` rerun on live SEC data; `docs/COVERAGE.md` regenerated.
  The script now also records the four red-flag scores for each company's latest year: a "Red flags"
  count column, a "Red flags unavailable" column with the reason for each missing score, and a summary
  line. The five line items added in session 5 appear in the missing / partly missing columns like the
  others.
- **2026-11-13 · result:** unchanged from 2026-11-12 for everything that was there before (29 of 30
  load, 8 with all 19 metrics, 20 of 29 balance; every company's metric count, years and balance
  failures are identical). Red flags: Altman Z″ 20 of 29, Piotroski F 19, Beneish M 18, accruals ratio
  29. A new hand-written section explains the gaps: every one comes from a missing line item, mostly
  the known issues #29, #31, #33 and #1. **Not filed:** three one-company gaps (NVO property, SONY
  receivables, BABA retained earnings).
- **2026-11-13 · checked:** 271 tests pass; the script isn't part of them (it needs the network).

## S6 Task 3 — LEARNING.md suggestions added

- **2026-11-13 · done:** the 18 terms suggested in sessions 2–5 (10 suggestion notes in this log, S2
  tasks 4, 5, 6; S3 tasks 2, 3; S4 task 3; S5 tasks 1–4) are now in `LEARNING.md`.
- **2026-11-13 · decision:** `LEARNING.md` has no headings; its "sections" are groups of lines: tools,
  a who-is-each-file-for table, a glossary of `Term: explanation.` lines, then notes on XBRL. Every
  suggestion is a term, so they went into the glossary group, right after its last line ("Cache: …"),
  in the order they were suggested and in the same `Term: explanation.` style (with the file's curly
  quotes). The suggestions' wording is kept, apart from that format.
- **2026-11-13 · checked:** `git diff` shows 18 lines added and 0 removed or changed.
  **Not included:** session 1's suggestions (the queue said sessions 2–5).

## S6 Task 4 — Changelog 1.2.0 and version bump

- **2026-11-13 · done:** `CHANGELOG.md` has a 1.2.0 section for session 5: red-flag scores and the five
  line items behind them, peers, TTM, industry benchmarks, shareable links, pre-load, and known limits.
  `pyproject.toml` is 1.2.0 and `uv lock` changed only the project's own version line.
- **2026-11-13 · decision:** dated 2026-11-13, the day session 5 was merged into `master`. No git tag
  (none exists for earlier versions either).
- **2026-11-13 · decision:** 1.2.0 covers session 5 only, as asked. This session's changes (coverage
  rerun, LEARNING.md, TYGO, red flags on compare and in Excel) aren't in it; the 1.2.0 known limits
  still say red flags are missing from compare and Excel, which is true of 1.2.0 itself. They'd go in
  the next version's notes.
- **2026-11-13 · included as a known limit:** the live app asks for a login (see S6 task 1).
- **2026-11-13 · checked:** 271 tests pass.

## S6 Task 5 — Revenue tagged twice at the wrong scale (Tigo Energy)

- **2026-11-13 · done:** when another revenue tag gives the same fiscal year exactly 1,000× or
  1,000,000× smaller than the chosen figure (within 0.1%, for rounding), the parser uses the smaller one
  and labels the row "revenue was also tagged 1,000× larger; the smaller figure is used". It's the same
  rule as `scripts/build_peers.py`. Because the trailing-twelve-months view reuses the annual rules, it
  gets the fix too.
- **2026-11-13 · decision:** revenue only, as asked. Tigo's other lines (cost of revenue, profit,
  assets) were already at the right scale. **Not covered:** the "single quarters" expander in the TTM
  view reads tags directly and would still show the larger figure for an affected company.
- **2026-11-13 · result:** Tigo Energy's revenue for FY2022–FY2025 drops from $81.3bn–$145.2bn to
  $81.3M–$145.2M; FY2025 gross margin 42.8% and asset turnover 1.37× (before: revenue 1,300× its assets).
  Every parsed row for the other 40 companies is unchanged (15,032 rows compared).
- **2026-11-13 · checked:** 275 tests pass (271 before), including a ratio that is 2× or 500× (left
  alone: goods-only revenue beside total revenue is normal).

## S6 Task 6 — Red-flag scores on the compare page and in the Excel export

- **2026-11-13 · compare page:** four rows, Altman Z″, Piotroski F, Beneish M and accruals ratio, sit
  between the ratios and the five valuation rows, each with its verdict ("3.20 · Safe zone",
  "-1.15 · ⚠ Flag"), the same short form as the company page's red-flag table. A missing score reads "—"
  and its reason is listed under "Why some values are missing". The caption under the table says which
  rows are which. **Not added:** the scores to the "Over time" chart (not asked).
- **2026-11-13 · Excel export, decision on "formulas only where simple":**
  - **Altman Z″ and the accruals ratio are live formulas** over the line-items sheet, like the other
    metrics: each is one sum of ratios with no conditions.
  - **Piotroski F and Beneish M are values**, with every input in the cell's comment: the nine tests
    with pass or fail, and the eight indexes with the line items behind them. As formulas they would be
    nine IF() tests and eight nested ratios each, too long to read or trust.
  - A year the engine can't score reads "n/a" with the reason as a comment, as for every metric.
- **2026-11-13 · checked:** the workbook's red-flag cells for AAPL, NVDA, SAP, WMT and JPM (352 cells
  over every stored year) equal the engine's values: formulas evaluated in Python agree exactly, and
  the stored values differ only in the 16th digit (Excel keeps 15). The Apple and Coca-Cola hand
  calculations from `tests/test_red_flags.py` are now also tested through the workbook. Compare page
  checked in a real browser (AAPL, KO, NVDA), no errors. 277 tests pass (275 before).

## S7 Task 1 — Design system

- **2026-11-13 · decision:** `DESIGN.md` written first; it sets the palette (navy/slate, one blue accent,
  green and red only for up/down), Inter, 8px radius, the metric-card, table, header, tab, chart and
  state rules. Every later UI task follows it.
- **2026-11-13 · decision:** the theme does almost all the work: `.streamlit/config.toml` defines
  `[theme.light]` and `[theme.dark]` (Streamlit follows the visitor's system setting; its menu switches),
  Inter from Google Fonts, sizes, radius and the four series colours. `style.css` (about 30 lines) only
  does what the theme can't: content width, tabular figures, the sticky header and the landing hero.
  **Why:** a theme option survives Streamlit upgrades; CSS against its internals may not.
- **2026-11-13 · decision:** Streamlit exposes no theme colours to CSS (checked in the browser: no
  `--st-*` variables), and `st.context.theme` can be wrong on first load, so every CSS colour is
  translucent and the sticky header is frosted (blur) instead of solid. **Rejected:** a solid header
  colour per theme (would be wrong after switching themes in the menu).
- **2026-11-13 · decision:** the "shared Plotly template" is `charts.style()`, which sets layout values
  rather than a `template`. **Why:** Streamlit replaces a figure's template with its own theme (which is
  what makes text readable in dark mode) but keeps layout values the figure sets itself.
- **2026-11-13 · decision:** the browser tab says "Datadough" (the live app's name) instead of
  "Finance Analyzer", with a chart icon.
- **2026-11-13 · checked:** Playwright through `uvx` with the cached Chromium, as in session 2 (the
  Playwright plugin still wants Google Chrome): Inter is applied, the dark background is `#0B1220`, no
  console errors. 278 tests pass.

## S7 Task 2 — Landing page

- **2026-11-13 · decision:** a new **Home** page is the default; navigation moved from the sidebar to the
  top (`st.navigation(position="top")`), the usual place on a research site. Hero: a "Datadough" badge,
  the headline, one sentence, a 52px search box ("Search any company or ticker") and example chips
  (`st.pills`). Three tiles (Analyse, Compare, Learn), each with a one-click start (Apple; AAPL, MSFT,
  NVDA; Coca-Cola). Footer on every page: SEC EDGAR and Yahoo Finance as sources, "not investment
  advice", a GitHub link. **Rejected:** a centred hero (Streamlit's input widths fight centring; left
  aligned reads like Stripe/Koyfin anyway).
- **2026-11-13 · decision:** picking a company on Home fills the company page's search box and switches
  page (the same mechanism the peer buttons already use), so the company page stays the one place that
  resolves typed text. `?ticker=AAPL` links now switch from Home to the company page; `?compare=` was
  already handled. Old links keep working (tested).
- **2026-11-13 · decision:** `toolbarMode = "viewer"` hides Streamlit's developer menu items ("Deploy");
  the settings menu with the light/dark switch stays.
- **2026-11-13 · scope:** a landing page isn't one of SPEC.md's screens; it adds no feature, only a way
  in, so SPEC.md is unchanged.
- **2026-11-13 · checked:** screenshots at 1400px light and 390px dark; no console errors. 280 tests pass.

## S7 Task 3 — Company page layout

- **2026-11-13 · decision:** the page is now a header plus six tabs (`st.tabs`): Overview · Financials ·
  Ratios · Red flags · Valuation · Data checks. Every tab opens with a one-line caption. The search box
  stays at the top, label hidden. The Period switch became a segmented control above the tabs, because it
  changes every tab.
- **2026-11-13 · decision (header):** name and ticker, badges for the exchange and the SIC industry, the
  share price with today's change, Refresh, Excel and a Share popover holding the link (`st.code` has a
  copy button). Sticky while scrolling on desktop; normal flow on phones, where a sticky block would take
  half the screen. **New data:** `Quote.previous_close` (Yahoo's `previousClose`; a missing one only hides
  the day change) and `exchange` from the SEC submissions file (empty when the SEC lists none).
- **2026-11-13 · decision (Overview):** four cards with sparklines and year-on-year arrows (revenue, net
  income, operating margin, free cash flow), the revenue and net-income bar chart, a "Key ratios vs
  industry" table (seven ratios, company and median), and the peers. **Why these four:** size, profit,
  efficiency and cash, the first things a case study asks.
- **2026-11-13 · decision:** the "SEC data loaded…" note moved from under the Refresh button into the Data
  checks tab, which is about where the data came from.
- **2026-11-13 · decision:** tab contents all run on every page view (Streamlit's default), so switching
  tabs is instant and the tests see every tab. **Rejected:** lazy tabs (a rerun on each click).
- **2026-11-13 · found while checking:** a running server keeps old copies of imported modules, so after
  this change the app must be restarted (a fresh deploy does this anyway).
- **2026-11-13 · checked:** AAPL Overview, Financials and Ratios in the browser; 282 tests pass.
