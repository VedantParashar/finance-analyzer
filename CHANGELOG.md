# Changelog

What each version added, newest first. Dates are year-month-day.

## 1.0.0 — 2026-11-11

The first complete version: everything in [SPEC.md](SPEC.md)'s v1 scope.
Live at https://datadough.streamlit.app.

### Data
- Financial statements for any US company from the SEC EDGAR "company facts" API, from a ticker.
- A standard schema of 23 line items (income statement, balance sheet, cash flow), each with a
  priority list of XBRL tags, stored in a local DuckDB file.
- Annual figures from 10-K and 10-K/A filings, de-duplicated so the latest filing wins.
- Per-share values and share counts adjusted for stock splits.
- Items some companies only report in parts are built from those parts and labelled as calculated:
  short-term debt, short-term investments, temporary equity, total liabilities.
- Downloads cached on disk, refreshed after 7 days or with the **Refresh data** button.
- Share price and market cap from Yahoo Finance (yfinance).

### Metrics
- 15 ratios: gross, operating and net margin; ROE, ROA, ROIC; current and quick ratio; debt/equity,
  interest coverage; asset turnover; free cash flow and FCF margin; revenue and EPS growth.
- Extras: equity multiplier, 3-year revenue and EPS growth rates, and the DuPont breakdown of ROE.
- Valuation at today's price: market cap, P/E, P/B, EV/EBIT and FCF yield. They read "unavailable"
  if Yahoo Finance doesn't answer.
- Every metric returns the inputs it used and, when it can't be calculated, the reason.

### Screens
- **Company page:** five years of line items, metric cards with the change on last year, trend charts,
  the DuPont breakdown and valuation.
- **Compare page:** 2 to 4 companies side by side, a chart of any metric over time, and a note when
  fiscal years end on different dates.
- **Excel export:** a workbook whose metric cells are live formulas over the line-item sheet.
- **Learning layer:** for every metric, the formula filled in with the company's numbers, what it
  means, what a good value looks like and common traps.

### Data checks
- Assets = liabilities + equity, checked for every stored year and shown with the size of any gap.
- Missing years flagged, with which ratios they affect.
- A warning banner for banks, brokers and insurers (SIC 6000–6499), whose statements don't fit the
  standard ratios.

### Project
- 148 automated tests, run on GitHub Actions for every push and pull request.
- One-command Docker setup (`docker compose up --build`).
- Hosted on Streamlit Community Cloud; steps in [DEPLOY.md](DEPLOY.md).
- MIT license.

### Known limits
- US filers of 10-K only; no foreign filers (20-F), ETFs or quarterly data.
- Open data issues: [#1](https://github.com/VedantParashar/finance-analyzer/issues/1),
  [#2](https://github.com/VedantParashar/finance-analyzer/issues/2),
  [#5](https://github.com/VedantParashar/finance-analyzer/issues/5),
  [#6](https://github.com/VedantParashar/finance-analyzer/issues/6).
