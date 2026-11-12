# Changelog

What each version added, newest first. Dates are year-month-day.

## 1.1.0 — not released yet (notes prepared 2026-11-12)

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
