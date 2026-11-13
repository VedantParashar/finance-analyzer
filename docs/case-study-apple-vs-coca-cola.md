# Case study: Apple vs Coca-Cola

Two famously profitable companies, made comparable with Datadough's own numbers. Every figure below is
what the app shows (company page, Financials and Ratios tabs, or the compare page `?compare=AAPL,KO`),
and each one links to its filing in the app. Statements from the filings are quoted and cited. Anything
that isn't checked against a filing is marked **(not verified in a filing)**.

Years: Apple's fiscal year ends in late September (FY2026 ended 26 September 2026); Coca-Cola's ends on
31 December (FY2025). The latest years therefore cover different months.

## 1. Why is Apple's ROE 142%?

Return on equity = net income ÷ average shareholders' equity.

| Apple | FY2025 | FY2026 |
|---|---|---|
| Net income | $112,010M | $132,175M |
| Shareholders' equity at year end | $73,733M | $112,093M |
| Average equity | | $92,913M |
| **ROE** | 171.4% | **142.3%** |

ROE above 100% means the company earned more in one year than the book value of everything its
shareholders own in it. The cause is the denominator, not an unusually large profit: Apple's equity is
small for a company with $404,548M of assets, because it has returned more cash to shareholders over the
years than it kept. In FY2026 alone the cash flow statement shows **$86,390M of share repurchases and
$15,721M of dividends** against $132,175M of net income
([10-K for FY2026](https://www.sec.gov/Archives/edgar/data/320193/000032019326000026/0000320193-26-000026-index.htm),
statement of cash flows). Repurchased shares are taken off equity, so years of buybacks larger than
profits had pushed Apple's retained earnings below zero: **−$14,264M at the end of FY2025**, turning
positive (+$13,700M) only in FY2026.

ROE *fell* from 171% to 142% in FY2026 even though profit rose 18%, because equity grew faster
(+52%): Apple bought back less than it earned that year. A falling ROE here is not a sign of weakness,
which is the trap the app's learning text warns about: ROE rewards a small equity base however it got
small.

## 2. The DuPont comparison

DuPont splits ROE into three factors: how much profit each dollar of sales keeps, how many sales each
dollar of assets produces, and how much of the assets are funded by shareholders rather than debt.

| | Net margin | × Asset turnover | × Equity multiplier | = ROE |
|---|---|---|---|---|
| Apple FY2026 | 27.6% | 1.25× | 4.11× | 142.3% |
| Coca-Cola FY2025 | 27.3% | 0.47× | 3.60× | 46.0% |

- **Margins are almost the same.** Each keeps about 27 cents of net profit per dollar of revenue.
- **Asset turnover is the big difference: 2.7 times as high at Apple.** Coca-Cola holds about $2.14
  of assets (average for the year) for each dollar of revenue; Apple about $0.80. Why Coca-Cola's
  balance sheet is that heavy (goodwill and brands from acquisitions, stakes in bottlers) is general
  knowledge about the company, **not verified in a filing** here.
- **Leverage is similar** (4.1× against 3.6×), so it explains little of the gap this year. For Apple
  it was 5.5–6.3× in FY2022–25, which is why its ROE was even higher then.

The point for a stock pitch: both are excellent businesses by margin, but Apple turns its asset base
over far faster, and its tiny equity inflates ROE further. Compare ROIC or ROA (Apple 34.6%, Coca-Cola
12.8% in the compare table) for a measure less distorted by buybacks.

## 3. Coca-Cola's FY2024 cash flow drop

Coca-Cola's operating cash flow fell by 41% in FY2024 while its net income barely moved:

| Coca-Cola | FY2023 | FY2024 | FY2025 |
|---|---|---|---|
| Net income | $10,714M | $10,631M | $13,107M |
| Operating cash flow | $11,599M | $6,805M | $7,408M |
| Free cash flow | $9,747M | $4,741M | $5,296M |

The reason, in the company's own words (FY2024 10-K, "Cash Flows from Operating Activities"):

> "This decrease was primarily driven by the $6.0 billion IRS Tax Litigation Deposit, an unfavorable
> impact due to foreign currency exchange rate fluctuations, higher other tax payments, increased
> charitable donations, and the reduced operating cash flows resulting from the refranchising of our
> bottling operations."

([10-K for FY2024](https://www.sec.gov/Archives/edgar/data/21344/000002134425000011/ko-20241231.htm),
filed 2025-02-20.) The same 10-K says the IRS invoiced $6.0 billion, "the total liability for the 2007
through 2009 tax years resulting from the Tax Court's decision" with interest, and that the company paid
it on 10 September 2024, "which stopped interest from accruing". The Tax Court's opinions concern the
company's foreign licensees, and Coca-Cola is appealing (Note 12).

Two lessons the app's numbers make visible:

- **Net income and cash can diverge for a year.** The 10-K treats the deposit as money it could get
  back: if the appeal fails, it "would not receive a refund of the applicable portion or all of the
  $6.0 billion it paid". So the payment left operating cash flow in 2024 (Note 21 shows a $5,667M
  increase in prepaid expenses and other assets) without the same charge to profit. The accruals ratio
  in the Red flags tab is 5.6% for FY2025, below the 10% flag line.
- **Free cash flow has stayed low in FY2025 ($5,296M).** Why it didn't recover is **not verified in a
  filing**: the FY2025 10-K hasn't been checked for this study.

## How to reproduce

Open `?compare=AAPL,KO` in the app for the table, then each company page: the Ratios tab for ROE and
DuPont (the "How it's calculated" popover shows each input and its filing), Financials for the line
items. Figures are as loaded on 2026-11-14; a later filing or restatement can change them.
