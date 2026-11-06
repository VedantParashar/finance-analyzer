# Finance Analyzer — Spec (v1)

## Goal
A free, open-source app that helps students analyse and compare public companies, and teaches what each number means.

## Users
Finance and business students doing case studies, stock pitches and theses.

## v1 scope (US companies only)

**Input & data**
- Input: a stock ticker.
- Financial statements: SEC EDGAR XBRL "company facts" API.
- Share price and market cap: yfinance.
- Storage: DuckDB, local file.

**Standard schema**
- About 40 line items, including revenue, COGS, operating income, net income, total assets, total liabilities, total debt, equity, operating cash flow and capex.

**Metrics (15 ratios + DuPont)**
- Profitability: gross margin, operating margin, net margin
- Returns: ROE, ROA, ROIC
- Liquidity: current ratio, quick ratio
- Leverage: debt/equity, interest coverage
- Efficiency: asset turnover
- Cash flow: free cash flow, FCF margin
- Growth: revenue growth, EPS growth
- DuPont breakdown of ROE

**Learning layer** (for every metric)
- The formula, filled in with the company's real numbers
- What it means
- What a good value looks like
- Common traps

**Screens**
- Single-company dashboard with 5-year trends
- Compare 2–4 companies
- Excel export with live formulas

**Data checks**
- Assets = liabilities + equity
- Missing years flagged

## Architecture
```
data adapters → standard schema → metrics engine → Streamlit UI
```
- **Data adapters**: fetch from EDGAR and yfinance, then map the results onto the standard schema.
- **Standard schema**: one shape for every company, stored in DuckDB.
- **Metrics engine**: a separate package that computes ratios from the schema, tested with pytest.
- **Streamlit UI**: the screens; it only displays what the engine computes.

## Out of scope for v1
- EU companies
- PDF upload
- LLM summaries
- Red-flag scores
- Banks and insurers
## “Open questions — decided”
EPS: add EarningsPerShareDiluted and the share count to the schema
If yfinance breaks: price-based metrics (P/E, market cap) show “unavailable”; everything else still works
Banks/insurers: show a warning (“ratios like gross margin don’t apply”), not a hard refusal