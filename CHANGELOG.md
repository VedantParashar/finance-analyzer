# Changelog

What each version added, newest first. Dates are year-month-day.

## 1.4.0 — unreleased

Data you can trace and check: every number links to its filing, the rules and the measured accuracy are
written down, and three kinds of wrong figures are fixed.

### Added
- **Trace any number:** a Source column in Financials (form type, filing date, link to the filing on
  sec.gov) and a filing link next to every input in "How it's calculated".
- **[METHODOLOGY.md](docs/METHODOLOGY.md):** how each number is chosen, with real examples (Apple's
  restated FY2008, NVIDIA's splits, Coca-Cola's liabilities, TSMC's and Novo Nordisk's bonds).
- **[ACCURACY.md](docs/ACCURACY.md) and `scripts/accuracy.py`:** 95 headline figures for 10 companies
  checked against the filings' own statements; 93 match, and both differences are explained.
- **Feedback:** a Feedback link when `FEEDBACK_URL` is set (https only), and "Report a wrong number" on
  every metric, opening a prefilled GitHub issue.
- **Docs and repo:** a rewritten README with a demo GIF, a case study (Apple vs Coca-Cola), a code of
  conduct, a security policy, a docs index, and the decision log moved to `docs/decision-log.md`.

### Changed
- **Revenue prefers total revenues** over revenue from contracts with customers when a company tags both.
  Eight of 55 companies change: Walmart (+1%, membership income now included), American Tower (FY2025
  $936M → $10,645M: rent was missing), Welltower, Berkshire Hathaway, Pfizer FY2021, Mastercard
  FY2018–19 (net instead of gross revenue), Occidental and Chevron (its "total revenues and other income"
  now counts, which includes non-revenue income).

### Fixed
- **Share counts filed in thousands** are multiplied back when net income ÷ EPS shows it (#72): NVIDIA
  FY2008–09, Advance Auto Parts FY2008 and Crocs FY2012.

### Known limits
- Chevron's revenue now includes other income (see above).
- `peers.json` keeps last year's revenue under the old tag order until it's rebuilt.
- Companies already saved in a local database keep their old figures until they're reloaded (Refresh,
  or the 7-day refresh). The hosted app starts empty after a restart.

## 1.3.0 — 2026-11-13

A redesign that makes the app look like a financial research site, operating income for companies
that don't report it, and FFO for REITs.

### Added
- **A design system** (`DESIGN.md`): a light and a dark theme (deep navy, one blue accent, green and red
  only for up and down), the Inter font, one chart style for every chart, and rules for cards, tables,
  tabs and loading, empty and error states. The app follows the visitor's system setting; the ⋮ menu
  switches it.
- **A home page** with a big search box, example tickers, three tiles (Analyse, Compare, Learn) and a
  footer naming the data sources and saying it's not investment advice. Navigation moved to the top.
- **Company page in tabs:** Overview · Financials · Ratios · Red flags · Valuation · Data checks, under a
  header that stays on screen with the exchange, industry, today's share price and change, and the
  Refresh, Excel and Share buttons. The Overview has four headline cards, the revenue and profit chart
  and key ratios next to the industry median.
- **Metric cards** with a sparkline of the years shown and a "How it's calculated" popover holding the
  formula, the learning text and any notes (the expanders are gone).
- **Financial tables** with the first column pinned, figures right-aligned in millions with the unit in
  the header, and negative numbers in red and in parentheses.
- **Compare page:** each company keeps one colour in its chip, its table column and its chart line; the
  best and worst value in each row are marked; the chart is picked by group and metric.
- **Operating income where none is reported** (#29): revenue − cost of revenue − operating expenses
  where tagged, otherwise EBIT (pretax income + interest expense), always marked as calculated and never
  used for banks, brokers or insurers. Chevron, Occidental, Pfizer, Lilly, Shell and Canadian Natural now
  have operating margin, ROIC, interest coverage, EV/EBIT and Altman Z″.
- **FFO (funds from operations) for REITs** (SIC 6798), with learning text and a live Excel formula, and
  a new line item for gains on sale of real estate.
- Browser tabs name the company or comparison; loading messages name the company.

### Changed
- Amounts in tables are now plain millions (`478,834`) with the unit in the header; cards still read
  `$478,834M`.
- The "SEC data loaded…" note moved to the Data checks tab.

### Known limits
- FFO adds back all depreciation and amortization (no REIT tags the real-estate part alone) and
  doesn't add back impairments, so it can differ from a REIT's own FFO. Realty Income still has no
  operating income for FY2024–25 (no interest expense tagged).
- The rest of #31 (REIT banner, property purchases as capital expenditure) is still open.
- On a phone the header's price and buttons sit right-aligned under the name.

## 1.2.0 — 2026-11-13

Red-flag scores, peers, the trailing twelve months, industry benchmarks and shareable links.

### Added
- **Red-flag scores**, every year, in a "Red flags" section on the company page: Altman Z″, Piotroski F
  (out of 9), Beneish M and the accruals ratio, each with its verdict ("Safe zone", "⚠ Flag"), every
  input and learning text. Altman Z is the Z″ version, which uses balance-sheet equity instead of a
  share price, so its cut-offs (2.6 and 1.1) differ from the classic Z-score's.
- **Five new line items** that the scores need: SG&A, receivables, property/plant/equipment, retained
  earnings, and depreciation & amortization.
- **Peer suggestions:** five companies with the same SEC industry (SIC) code, closest in revenue first;
  one click opens the compare page. They come from a file shipped with the app (`peers.json`), rebuilt
  about once a year with `scripts/build_peers.py`.
- **Trailing twelve months (TTM):** a "Period" toggle on the company page switches every figure to the
  last four quarters, built from quarterly reports (Q4 = full year − first nine months), with the
  single quarters in an expander. Foreign filers file no quarterly data and stay on fiscal years.
- **Industry benchmarks:** each metric card shows the median for stored companies in the same 2-digit
  SIC group, once there are at least 3 of them.
- **Shareable links:** `?ticker=AAPL` opens a company and `?compare=AAPL,KO` a comparison; the address
  follows what's on screen, so copying it shares the view.
- **Pre-load on the hosted app:** after a restart, the 30 stress-test companies load in the background,
  so their first view takes about 1 second instead of 2 (measured locally).

### Known limits
- Red-flag scores aren't on the compare page or in the Excel export yet.
- Industry medians use only the companies loaded into the app, so the sample is small and varies.
- In TTM view, banks and a few companies that tag quarterly figures differently have fewer metrics.
- The live app currently asks visitors to log in (found 2026-11-13); its sharing setting needs checking.

## 1.1.0 — 2026-11-12

Search that picks the right company, valuation ratios for foreign companies, and TSMC's debt fixed.

### Added
- **Valuation for foreign filers:** P/E, P/B, EV/EBIT and FCF yield now work for companies that don't
  report in US dollars (TSMC, ASML, SAP, Toyota). Market cap is converted into the company's reporting
  currency at today's exchange rate from Yahoo Finance; the page shows the rate and its date. If the
  rate can't be fetched, the four ratios read "unavailable". Financial statements are still shown as
  reported, never converted.
- **40-F/A** (an amended Canadian annual report) is accepted, beside 10-K/A and 20-F/A.

### Fixed
- **Compare page search:** typing a ticker and pressing Enter now always picks that ticker. Before,
  "F" or "MA" could pick a larger company that merely contained those letters.
  The trade-off: on this page a company name is suggested from its first word only ("Coca", not "Cola").
- **TSMC's debt** ([#26](https://github.com/VedantParashar/finance-analyzer/issues/26)): its bonds are
  now counted, so debt/equity for FY2024 reads 0.24× instead of 0.02×. For companies reporting under
  IFRS, bonds are added when they are reported apart from borrowings; no other tested company changed.

### Removed
- `.devcontainer/`: an unused GitHub Codespaces setup that asked for Python 3.11 and a
  `requirements.txt`. The live app and local setup don't use it.

### Known limits
- TSMC's latest year is FY2024: the SEC's data feed has no statements from its FY2025 report
  ([#37](https://github.com/VedantParashar/finance-analyzer/issues/37)), so its valuation ratios look
  high.
- Toyota has no FCF yield, gross margin or free cash flow
  ([#27](https://github.com/VedantParashar/finance-analyzer/issues/27)).
- Open data issues from the 30-company stress test:
  [#29](https://github.com/VedantParashar/finance-analyzer/issues/29)–[#33](https://github.com/VedantParashar/finance-analyzer/issues/33).

## 1.0.0 — 2026-11-12

The first complete version: everything in [SPEC.md](SPEC.md)'s v1 scope.
Live at https://datadough.streamlit.app.

### Data
- Financial statements for any company that files annual reports with the SEC, from the SEC EDGAR
  "company facts" API: US companies (10-K) and foreign filers (20-F, 40-F), under US GAAP or IFRS.
  Foreign filers are shown in their reporting currency.
- **Search** by ticker or company name, with suggestions; BRK.B, BRK-B and `brk b` all work; separate
  messages for unknown tickers, funds and companies with no annual report.
- A standard schema of 23 line items (income statement, balance sheet, cash flow), each with a
  priority list of XBRL tags, stored in a local DuckDB file.
- Annual figures from 10-K, 20-F and 40-F filings and their amendments, de-duplicated so the latest
  filing wins.
- Per-share values and share counts adjusted for stock splits.
- Items some companies only report in parts are built from those parts and labelled as calculated:
  short-term debt, short-term investments, temporary equity, total liabilities, shareholders' equity,
  and cash where only the total including restricted cash is tagged.
- Downloads cached on disk, refreshed after 7 days or with the **Refresh data** button.
- Share price and market cap from Yahoo Finance (yfinance).

### Metrics
- 15 ratios: gross, operating and net margin; ROE, ROA, ROIC; current and quick ratio; debt/equity,
  interest coverage; asset turnover; free cash flow and FCF margin; revenue and EPS growth.
- Extras: equity multiplier, 3-year revenue and EPS growth rates, and the DuPont breakdown of ROE.
- Valuation at today's price: market cap, P/E, P/B, EV/EBIT and FCF yield. They read "unavailable"
  if Yahoo Finance doesn't answer, and for companies that don't report in US dollars.
- Every metric returns the inputs it used and, when it can't be calculated, the reason.

### Screens
- **Company page:** five years of line items, metric cards with the change on last year, trend charts,
  the DuPont breakdown and valuation.
- **Compare page:** 2 to 4 companies side by side, a chart of any metric over time, and a note when
  fiscal years end on different dates or the companies report in different currencies.
- **Excel export:** a workbook whose metric cells are live formulas over the line-item sheet.
- **Learning layer:** for every metric, the formula filled in with the company's numbers, what it
  means, what a good value looks like and common traps.

### Data checks
- Assets = liabilities + equity, checked for every stored year and shown with the size of any gap.
- Missing years flagged, with which ratios they affect.
- A warning banner for banks, brokers and insurers (SIC 6000–6499), whose statements don't fit the
  standard ratios.
- A stress test on 30 very different companies, with every gap recorded in
  [docs/COVERAGE.md](docs/COVERAGE.md) (`scripts/coverage.py` reruns it).

### Project
- 190 automated tests, run on GitHub Actions for every push and pull request.
- One-command Docker setup (`docker compose up --build`).
- Hosted on Streamlit Community Cloud; steps in [DEPLOY.md](DEPLOY.md).
- MIT license, CONTRIBUTING.md, this changelog, and issue templates for bugs and feature requests.

### Known limits
- No ETFs or funds, no quarterly data, and no valuation ratios for companies that don't report in
  US dollars.
- Open data issues: [#1](https://github.com/VedantParashar/finance-analyzer/issues/1),
  [#2](https://github.com/VedantParashar/finance-analyzer/issues/2),
  [#5](https://github.com/VedantParashar/finance-analyzer/issues/5),
  [#6](https://github.com/VedantParashar/finance-analyzer/issues/6),
  [#26](https://github.com/VedantParashar/finance-analyzer/issues/26),
  [#27](https://github.com/VedantParashar/finance-analyzer/issues/27) and
  [#29](https://github.com/VedantParashar/finance-analyzer/issues/29)–[#33](https://github.com/VedantParashar/finance-analyzer/issues/33).
