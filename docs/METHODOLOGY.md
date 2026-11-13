# Methodology: how each number is chosen

Every figure in Datadough comes from the XBRL data companies file with the US SEC (the "company facts"
API). That data holds many candidate values for the same thing: different tags, quarterly and annual
periods, and the same year repeated in later filings, sometimes changed. These rules decide which value
is shown. Each has a real example, and each value on screen links to the filing it came from
(Financials → Source, or "How it's calculated" on any metric).

The code lives in `src/finance_analyzer/parse.py` (choosing and deriving line items) and
`schema.py` (which tags feed each line item).

## 1. Tag priority

Each line item has an ordered list of XBRL tags (`schema.py`). All of them are read; when two tags give a
value for the same year in the same filing, the earlier tag in the list wins. Companies that report under
IFRS (most foreign filers) have their own list under `IFRS_TAGS`.

> **Example:** revenue. Companies moved from `SalesRevenueNet` / `Revenues` to
> `RevenueFromContractWithCustomerExcludingAssessedTax` when the ASC 606 revenue standard arrived in 2018,
> so that tag comes first and the older ones fill the earlier years. Utilities (NextEra, Duke) use
> `RegulatedAndUnregulatedOperatingRevenue`, which is further down the list.

## 2. Annual periods only

A value counts as a fiscal year only if it comes from an annual report (10-K, 20-F, 40-F or an amended
one) **and** covers 350–380 days. Income and cash-flow figures inside a 10-K also include quarters and
prior years; the day count drops the quarters. Balance-sheet values (a single date) count only on a
fiscal year end.

> **Example:** Apple's fiscal years run 52 or 53 weeks. FY2023 (25 September 2022 to 30 September 2023) is
> 370 days from start date to end date and FY2024 is 363; both pass. A fourth-quarter figure (about 90
> days) does not.

## 3. The latest filing wins (restatements)

The same year appears in up to three annual reports, as the current year and then as a comparison. When
the values differ, the one from the **most recently filed** report is used, because a company restates a
year to correct or re-present it.

> **Example: Apple FY2008.** The 10-K filed 2009-10-27 reports FY2008 revenue of $32,479M and diluted EPS
> of $5.36. After a change in how iPhone revenue was recognised, the 10-K/A filed 2010-01-25 and the 10-K
> filed 2010-10-27 restate FY2008 to $37,491M and $6.78. The app shows the restated $37,491M.

## 4. Stock splits

Per-share values and share counts from before a split are rescaled to today's share basis, so EPS growth
compares like with like. A split is detected when a later filing reports an earlier year's EPS at a clean
ratio of the original (any whole number, or 5-for-4 and 3-for-2; reverse splits too), **and** net income for that year is unchanged within
1%, which rules out a restatement. Rescaled values say so: "split-adjusted ÷10".

> **Example: NVIDIA.** It split 4-for-1 in 2021 and 10-for-1 in 2024. FY2022 diluted EPS was filed as
> $3.85; the app shows $0.385 ("split-adjusted ÷10"), and years before the 2021 split are divided by 40.
> Apple's FY2008 EPS change ($5.36 → $6.78, above) is *not* treated as a split: its net income moved too.

## 5. Derived items

When a line item isn't tagged, the app calculates it from items that are, **only** by a rule that holds
by definition, and labels it (`*` in tables, the formula in the footnote and the popover). It never fills
a gap with a guess.

| Derived item | Rule |
|---|---|
| Total liabilities | total liabilities and equity − total equity (− temporary equity) |
| Short-term debt | commercial paper + other short-term borrowings + current maturities of long-term debt |
| Shareholders' equity | total equity − minority interest |
| SG&A | selling and marketing + general and administrative |
| Operating income | revenue − cost of revenue − operating expenses; otherwise EBIT (pretax income + interest expense), never for banks |
| Debt (IFRS) | borrowings + bonds, when the bonds are reported apart from borrowings |

> **Example: Coca-Cola's liabilities.** KO never tags a total-liabilities figure; it tags total
> liabilities *and equity* and total equity. FY2025: liabilities = total − equity = $70,541M, marked
> "liabilities = total − equity".
>
> **Example: TSMC's bonds.** Under IFRS, TSMC reports TWD 926.6bn of bonds on a separate line from
> borrowings of TWD 31.8bn. Counting borrowings only showed debt/equity of 0.02×; adding the bonds gives
> FY2024 long-term debt of TWD 958.4bn and 0.24×.
>
> **Example: Novo Nordisk.** Novo reports long-term borrowings of DKK 118.9bn and tags the DKK 111.4bn of
> bonds *inside* that figure. Adding them would have shown DKK 230bn, nearly double the truth. So bonds
> are added only when they're larger than the borrowings figure: a part can't be bigger than its whole.

## 6. The balance check

For every stored year the app tests: total assets = total liabilities + temporary equity + total equity,
allowing 0.1% of total assets for rounding. Results are on the Data checks tab, year by year. A failure
doesn't change any number; it tells you to read that year's balance sheet yourself. The usual cause is an
older year restated line by line in a later filing (issue #30).

## 7. Absent is not zero

A missing value stays missing ("—", and the metric says why: "interest_expense not reported for
FY2026"). The one exception is a short list of items that many companies simply don't have (inventory,
short-term debt, long-term debt, short-term investments, gains on sale of real estate). They count as 0
**only if the company has never reported them in any year**, with a visible note ("inventory assumed 0
(never reported)").

> **Example:** Apple reported interest expense up to FY2023 and stopped. Its interest coverage for FY2026
> is "unavailable", not infinite: an item that disappears isn't assumed to have become zero (issue #1).

## 8. Currency

Figures stay in the currency the company reports in (Novo Nordisk in DKK, TSMC in TWD). Only for the
valuation ratios is the market cap (from Yahoo Finance, in dollars) converted, at today's rate, which is
shown with its date.

## What these rules can't catch

- A value tagged with the wrong scale (thousands instead of units) where no second tag gives the right
  one. One known case: revenue tagged twice at a 1,000× difference is caught (Tigo Energy); other items
  aren't checked for this.
- A company that uses a tag nobody else uses for a common line. Those show as "not reported" and are
  listed in [COVERAGE.md](COVERAGE.md).
- How the app's figures compare with the filings themselves is measured in [ACCURACY.md](ACCURACY.md).
