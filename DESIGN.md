# Datadough design system

The look we aim for: a calm, dense financial research site (Koyfin, Finviz, a Stripe dashboard), not a
default Streamlit page. Numbers come first; decoration is close to zero. Every UI change follows this file.

## Where it lives

| Piece | File |
|---|---|
| Colours, fonts, radius, light and dark themes | `.streamlit/config.toml` |
| The few things the theme can't do (sticky header, card spacing, tabular figures) | `src/finance_analyzer/style.css` |
| Chart look, shared by every chart | `src/finance_analyzer/charts.py` |
| Number formatting | `src/finance_analyzer/display.py` |

Prefer a theme option or a Streamlit parameter over CSS. CSS only targets Streamlit's stable hooks:
`st-key-<key>` classes on keyed containers and `data-testid` attributes.

## Colour

One accent colour. Green and red mean **up and down only**, never decoration or company identity.

| Token | Light | Dark | Use |
|---|---|---|---|
| background | `#FFFFFF` | `#0B1220` (deep navy) | page |
| surface | `#F4F6FA` | `#121B2E` | cards, inputs, sidebar, table headers |
| border | `#E2E8F0` | `#1F2A40` | card and table borders |
| text | `#0F172A` (slate 900) | `#E2E8F0` (slate 200) | body text and numbers |
| muted | `#64748B` (slate 500) | `#94A3B8` (slate 400) | captions, axis labels, units |
| accent | `#2563EB` | `#3B82F6` | buttons, links, active tab, the first series in a chart |
| up | `#15803D` | `#22C55E` | positive change |
| down | `#DC2626` | `#F87171` | negative change, negative numbers in tables |

**Series colours** (companies on the compare page, several lines in one chart), in this order:
`#2563EB` blue · `#F59E0B` amber · `#8B5CF6` violet · `#06B6D4` cyan. A company keeps its colour
everywhere on a page: its chip, its table column and its chart line.

Warnings (bank and REIT banners, failed balance checks) use Streamlit's own warning colours.

## Typography

- **Inter** for everything (Google Fonts, loaded by the theme), system sans-serif as the fallback.
- Numbers use tabular figures (`font-variant-numeric: tabular-nums`) so columns of digits line up.
- Sizes: page title 2rem/700 · section heading 1.25rem/600 · card label 0.8rem/500 muted · card value
  1.6rem/600 · body 0.95rem · captions 0.8rem muted.
- Sentence case everywhere ("Red flags", not "Red Flags"). No emoji in headings; ✓ ⚠ ✗ only in checks.

## Spacing and shape

- 4px grid: gaps of 8, 12, 16 or 24px. Sections are separated by 24px, not by dividers.
- Corner radius 8px on cards, inputs and buttons.
- Page width: wide layout, content capped at 1280px and centred.
- Mobile (below 640px): Streamlit stacks columns by itself; nothing may need horizontal scrolling except
  tables, which scroll inside themselves with the first column pinned.

## Components

**Metric card** (`metric_card()` in `app.py`): a bordered `st.metric` with
- the label, and the value in the card value size;
- a delta chip: the year-on-year change, green up or red down (inverted for debt/equity, where up is
  worse), with an arrow;
- a sparkline of the last five years when there are at least two values;
- an ⓘ popover holding the formula with the company's numbers, what it means, what's good, and the
  traps. Long text never sits on the card itself;
- at most one short caption below: the industry median, or why the value is missing.

**Financial table**: `st.dataframe` with
- the first column pinned (it stays put while the years scroll);
- numbers right-aligned, the unit in the header (`$M`), not in every cell;
- negative numbers in red and in parentheses: `(1,234)`;
- `—` for a value that isn't reported, never `0`; `*` after a value we calculated, with the footnote
  below the table.

**Page header** (company page): name, ticker, exchange and industry, the share price and today's change,
then the actions (Refresh, Excel export, share link) on the right. It stays at the top while scrolling.

**Tabs** for the sections of one company: Overview · Financials · Ratios · Red flags · Valuation · Data
checks. Every tab opens with a one-line caption saying what it shows.

**Chips**: `st.pills` / buttons for example tickers and company choices; `st.badge` for short status
(calculated, flag, safe zone).

**States**
- Loading: a spinner that says what is happening ("Loading Apple from SEC EDGAR…").
- Empty: say what to do next and offer an example to click.
- Error: say what went wrong in plain words and what to try; never a stack trace.

## Charts

Plotly, always through `charts.style()`, so every chart gets the same:
- Inter, 13px; title 15px/600, left-aligned; muted axis labels.
- Light horizontal gridlines only (`rgba(100,116,139,0.18)`), no vertical gridlines, no zero line
  emphasis unless values go negative.
- Transparent background, so the chart sits on the page colour in light and dark.
- Series colours from the list above, in order.
- Unified hover across series (`x unified`) with formatted values (`$391,035M`, `24.3%`).
- Legend above the chart, horizontal, no title. Height 320px; the plot margin is tight.
- Bars for amounts (revenue, profit), lines for ratios over time.
- Missing years are gaps, never zero.

## Number formatting

All in `display.py`, never inline in pages.
- Amounts: `$391,035M` on cards, `391,035` in tables with `$M` in the header; other currencies by code
  (`EUR 12,345M`).
- Percentages: one decimal (`24.3%`); percentage-point changes `+1.2 pp`.
- Multiples: two decimals with `×` (`1.07×`).
- Negative amounts in tables: `(1,234)`; elsewhere a leading minus.

## Light and dark

Both themes are defined in `config.toml` (`[theme.light]`, `[theme.dark]`); Streamlit follows the
visitor's system setting and its menu can switch. Never hard-code a colour in a page or CSS rule that is
only readable in one theme: use the theme's own colours (CSS variables) or a translucent colour.
