"""Stress test: load real companies and write what's missing to docs/COVERAGE.md.

Needs the network and SEC_USER_AGENT, so it is run by hand, not by the tests:

    uv run --env-file .env python scripts/coverage.py
"""

from datetime import date
from pathlib import Path

from finance_analyzer import display, edgar, parse, store
from finance_analyzer.metrics import FORMULAS, RED_FLAG_FORMULAS, company_metrics
from finance_analyzer.preload import GROUPS
from finance_analyzer.schema import ITEMS

# Written by hand after the 2026-11-12 run, red flags after the 2026-11-13 run; update it when the tables change.
FINDINGS = """## What the gaps have in common

| Pattern | Companies | Effect | Status |
|---|---|---|---|
| No operating income subtotal in the income statement | CVX, OXY, PFE, LLY, SHEL, CNQ, O | operating margin, ROIC, interest coverage unavailable | [#29](https://github.com/VedantParashar/finance-analyzer/issues/29) |
| An older year restated in a later filing, line by line | MSFT, WMT, COST, OXY, NEE, AMT, PLOW, SONY, CRWV | that year fails the balance check | [#30](https://github.com/VedantParashar/finance-analyzer/issues/30) |
| REITs: no current/non-current split, no cost of revenue or capex | O, PLD, AMT | liquidity ratios, gross margin, free cash flow unavailable | [#31](https://github.com/VedantParashar/finance-analyzer/issues/31) |
| The SEC's data has only quarterly reports | XOM | can't be loaded | [#32](https://github.com/VedantParashar/finance-analyzer/issues/32) |
| Cost of revenue and capex split over industry-specific tags | NEE, DUK, OXY, SHEL, CNQ, BABA | gross margin, free cash flow unavailable | [#33](https://github.com/VedantParashar/finance-analyzer/issues/33) |
| An item reported in earlier years, then absent (probably "none") | GOOGL, CALM, CROX, RIVN, MRNA | quick ratio, debt/equity or ROIC unavailable | [#1](https://github.com/VedantParashar/finance-analyzer/issues/1) |
| No interest expense tagged | MRNA, RDDT, NEE, PLOW | interest coverage unavailable | not filed: MRNA and RDDT have little or no debt; NEE tags only the interest it paid; PLOW not investigated |
| Losses, or fewer than four years of history | AMZN, CROX, MRNA, RDDT, CRWV, RIVN | EPS growth rates unavailable | correct: growth from a negative or missing base isn't meaningful |
| First stored year has no balance sheet | RDDT, CRWV | "partly missing" balance sheet items | correct: a first annual report repeats older income statements only |

Fixed during this run (all were missing before it):

- **Utilities' revenue** (NEE, DUK): added `RegulatedAndUnregulatedOperatingRevenue`. They went from 9 to 15 and 16 metrics.
- **Cash** (TGT, CVX, PLOW): where plain cash isn't tagged, the total including restricted cash is used and labelled.
- **Shareholders' equity** (NVO, CNQ, RIVN): where only total equity is tagged, it is total equity less any minority interest, labelled as calculated.
- **Interest expense** (OXY) and **capital expenditure** (LLY): one extra fallback tag each.

## Red-flag scores: why some are unavailable

Every gap comes from a line item a score needs; none is a fault in a score's formula.

| Missing input | Companies | Scores affected | Status |
|---|---|---|---|
| Operating income (no subtotal) | CVX, OXY, PFE, LLY, SHEL, CNQ | Altman Z″ | [#29](https://github.com/VedantParashar/finance-analyzer/issues/29) |
| Cost of revenue | OXY, NEE, DUK, AMT, SHEL, CNQ | Piotroski F, Beneish M | [#33](https://github.com/VedantParashar/finance-analyzer/issues/33) |
| Current assets, receivables (REITs) | O, PLD | all three except the accruals ratio | [#31](https://github.com/VedantParashar/finance-analyzer/issues/31) |
| Long-term debt never tagged in recent years (probably "none") | CALM, O | Piotroski F, Beneish M | [#1](https://github.com/VedantParashar/finance-analyzer/issues/1) |
| Property, plant and equipment in the latest year | NVO | Beneish M | not filed: reported in earlier years only |
| Receivables | SONY | Beneish M | not filed: Sony tags its own receivables lines |
| Retained earnings | BABA | Altman Z″ | not filed: no retained earnings tag in the latest year |
| Three consecutive years with a balance sheet | CRWV | Piotroski F | correct: listed in 2025 |

Of the five line items added for the scores, SG&A is missing for the two utilities (NEE, DUK), which
report no such line, and receivables, property and retained earnings for some REITs and foreign filers.
"""
RECENT_YEARS = 5
NOT_EXPECTED = {"temporary_equity"}  # most companies have none, so its absence isn't a gap


def check(ticker: str) -> dict:
    """Load one company and collect its gaps for the last RECENT_YEARS fiscal years."""
    try:
        store.load_company(ticker)
    except Exception as error:  # the point of a stress test is to record every kind of failure
        return {"error": f"{type(error).__name__}: {error}"}
    rows = store.get_company(ticker)
    metrics = company_metrics(rows)
    years = sorted(metrics)
    recent = years[-RECENT_YEARS:]
    have = {(row.item, row.fiscal_year_end) for row in rows}
    checks = parse.balance_checks(edgar.fetch_company_facts(ticker))
    latest = {name: metric for name, metric in metrics[years[-1]].items() if name in FORMULAS}  # not the red-flag scores
    flags = {name: metrics[years[-1]][name] for name in RED_FLAG_FORMULAS}
    return {
        "currency": display.currency(rows),
        "years": f"{display.fiscal_year(years[0])}–{display.fiscal_year(years[-1])}",
        "missing_items": [
            item for item in ITEMS
            if item not in NOT_EXPECTED and not any((item, end) in have for end in recent)
        ],
        "partial_items": [
            item for item in ITEMS
            if item not in NOT_EXPECTED and 0 < sum((item, end) in have for end in recent) < len(recent)
        ],
        "metrics_ok": sum(metric.value is not None for metric in latest.values()),
        "metrics_missing": [display.LABELS[name] for name, metric in latest.items() if metric.value is None],
        "balance_failures": [
            f"{display.fiscal_year(date.fromisoformat(c.fiscal_year_end))} ({display.money(c.difference, display.currency(rows))})"
            for c in checks if not c.passed
        ],
        "year_gaps": len(display.missing_years(years)),
        "flags_ok": [name for name, metric in flags.items() if metric.value is not None],
        "flags_missing": [f"{display.LABELS[name]} ({metric.reason})" for name, metric in flags.items() if metric.value is None],
    }


def main() -> None:
    results = {ticker: check(ticker) for tickers in GROUPS.values() for ticker in tickers}
    loaded = {ticker: result for ticker, result in results.items() if "error" not in result}
    lines = [
        "# Coverage: stress test on 30 companies",
        "",
        f"Generated by `scripts/coverage.py` on {date.today():%Y-%m-%d} from live SEC data. For each company it runs",
        "`store.load_company` and `metrics.company_metrics`, then lists what is missing.",
        "",
        f"- **Loaded:** {len(loaded)} of {len(results)}.",
        f"- **All 19 metrics for the latest year:** {sum(r['metrics_ok'] == 19 for r in loaded.values())} companies.",
        f"- **Every stored year balances:** {sum(not r['balance_failures'] for r in loaded.values())} of {len(loaded)}.",
        "- **Red-flag scores for the latest year:** "
        + ", ".join(f"{display.LABELS[name]} {sum(name in r['flags_ok'] for r in loaded.values())} of {len(loaded)}"
                    for name in RED_FLAG_FORMULAS) + ".",
        "",
        "How to read it: *Missing items* were not found in any of the last five fiscal years; *partly missing*",
        "in some of them. Temporary equity is left out (most companies have none). *Metrics* counts the 19",
        "ratios for the latest fiscal year; *Red flags* the four red-flag scores, with the first reason for",
        "each one that's unavailable. Balance failures cover every stored year, with assets minus",
        "(liabilities + equity).",
        "",
    ]
    lines += [FINDINGS]
    for group, tickers in GROUPS.items():
        lines += [f"## {group}", "", "| Ticker | Currency | Years | Metrics | Red flags | Missing items | Partly missing | Metrics unavailable | Red flags unavailable | Balance failures |", "|---|---|---|---|---|---|---|---|---|---|"]
        for ticker in tickers:
            r = results[ticker]
            if "error" in r:
                lines.append(f"| {ticker} | | | **failed** | | {r['error']} | | | | |")
                continue
            cells = [
                ticker, r["currency"], r["years"], f"{r['metrics_ok']} of 19", f"{len(r['flags_ok'])} of 4",
                ", ".join(r["missing_items"]) or "none", ", ".join(r["partial_items"]) or "none",
                ", ".join(r["metrics_missing"]) or "none", ", ".join(r["flags_missing"]) or "none",
                ", ".join(r["balance_failures"]) or "none",
            ]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    Path("docs/COVERAGE.md").write_text("\n".join(lines))
    print(f"wrote docs/COVERAGE.md: {len(loaded)} of {len(results)} loaded")


if __name__ == "__main__":
    main()
