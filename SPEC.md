# Finance Analyzer — Spec (v1)

## Goal
A free, open-source app that helps students analyse and compare public companies that file with the US SEC, and teaches what each number means.

## Users
Finance and business students doing case studies, stock pitches and theses.

## v1 scope (companies filing with the SEC, US GAAP or IFRS)

**Input & data**
- Input: a stock ticker or company name.
- Companies: any that file annual reports with the SEC: US companies (10-K) and foreign filers (20-F, 40-F), reporting under US GAAP or IFRS.
- Currency: figures are shown in the company's reporting currency and aren't converted. For the valuation ratios only, market cap is converted into that currency at today's exchange rate.
- Financial statements: SEC EDGAR XBRL "company facts" API.
- Share price, market cap and exchange rates: yfinance.
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
- Red-flag scores, per year: Altman Z″, Piotroski F, Beneish M, accruals ratio
- Real estate investment trusts (SIC 6798) only: funds from operations (FFO) = net income + depreciation and amortization − gains on sale of real estate

**Learning layer** (for every metric)
- The formula, filled in with the company's real numbers
- What it means
- What a good value looks like
- Common traps

**Screens**
- Single-company dashboard with 5-year trends, by fiscal year or trailing twelve months (from 10-Q reports; Q4 = full year − nine months)
- Compare 2–4 companies
- Industry benchmark next to each ratio: the median across stored companies in the same 2-digit SIC group
- Peer suggestions on the company page: 5 companies with the same SEC industry (SIC) code, closest in revenue
- Excel export with live formulas
- Shareable links: `?ticker=AAPL` opens a company, `?compare=AAPL,KO` a comparison

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
- Companies that don't file with the SEC (most EU and Asian companies without a US listing)
- Converting financial statements into another currency
- PDF upload
- LLM summaries
- Banks and insurers
## “Open questions — decided”
EPS: add EarningsPerShareDiluted and the share count to the schema
If yfinance breaks: price-based metrics (P/E, market cap) show “unavailable”; everything else still works
Banks/insurers: show a warning (“ratios like gross margin don’t apply”), not a hard refusal