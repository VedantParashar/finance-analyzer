"""Excel export: a line-items sheet and a metrics sheet whose cells are live formulas over it.

A metric cell only gets a formula when the engine could calculate that year; otherwise it says
"n/a" with the engine's reason as a cell comment, so Excel never shows a misleading #DIV/0!.
"""

from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from finance_analyzer import display
from finance_analyzer.metrics import FORMULA_TEXT, ZERO_IF_NEVER_REPORTED, Metric
from finance_analyzer.schema import ITEMS
from finance_analyzer.store import StoredLineItem

LINE_ITEMS = "Line items"
FIRST_YEAR_COLUMN = 3  # A = name, B = unit or formula text, C onwards = one column per fiscal year
UNITS = {"USD": ("$M", 1e6, "#,##0"), "USD/shares": ("$ per share", 1, "0.00"), "shares": ("M shares", 1e6, "#,##0")}
AUTHOR = "Finance Analyzer"


def _formulas(cell) -> dict[str, str]:
    """Excel formula bodies for each metric; cell(item, years_back) gives a reference into the line items."""

    def avg(item):
        return f"(({cell(item)}+{cell(item, 1)})/2)"

    def invested(back):
        return (f"({cell('short_term_debt', back)}+{cell('long_term_debt', back)}+{cell('total_equity', back)}"
                f"-{cell('cash', back)}-{cell('short_term_investments', back)})")

    def growth(item):
        return f"{cell(item)}/{cell(item, 1)}-1"

    def cagr(item):
        return f"({cell(item)}/{cell(item, 3)})^(1/3)-1"

    revenue, fcf = cell("revenue"), f"({cell('operating_cash_flow')}-{cell('capital_expenditure')})"
    return {
        "gross_margin": f"({revenue}-{cell('cost_of_revenue')})/{revenue}",
        "operating_margin": f"{cell('operating_income')}/{revenue}",
        "net_margin": f"{cell('net_income')}/{revenue}",
        "roe": f"{cell('net_income')}/{avg('shareholders_equity')}",
        "roa": f"{cell('net_income')}/{avg('total_assets')}",
        "roic": f"{cell('operating_income')}*(1-{cell('income_tax')}/{cell('pretax_income')})"
        f"/(({invested(0)}+{invested(1)})/2)",
        "current_ratio": f"{cell('current_assets')}/{cell('current_liabilities')}",
        "quick_ratio": f"({cell('current_assets')}-{cell('inventory')})/{cell('current_liabilities')}",
        "debt_to_equity": f"({cell('short_term_debt')}+{cell('long_term_debt')})/{cell('shareholders_equity')}",
        "interest_coverage": f"{cell('operating_income')}/{cell('interest_expense')}",
        "asset_turnover": f"{revenue}/{avg('total_assets')}",
        "free_cash_flow": fcf,
        "fcf_margin": f"{fcf}/{revenue}",
        "revenue_growth": growth("revenue"),
        "revenue_cagr_3y": cagr("revenue"),
        "eps_growth": growth("diluted_eps"),
        "eps_cagr_3y": cagr("diluted_eps"),
        "equity_multiplier": f"{avg('total_assets')}/{avg('shareholders_equity')}",
    }


def company_workbook(
    ticker: str, rows: list[StoredLineItem], metrics: dict[date, dict[str, Metric]]
) -> bytes:
    """The .xlsx file's bytes for one company, every stored year."""
    years = sorted(metrics)
    by_key = {(row.item, row.fiscal_year_end): row for row in rows}
    reported = {row.item for row in rows}
    currency = display.currency(rows)
    book = Workbook()

    # Every schema item gets a row, so formulas always point somewhere; gaps stay blank.
    items = book.active
    items.title = LINE_ITEMS
    items.append([f"{ticker} line items", "Unit", *map(display.fiscal_year, years)])
    item_rows = {}
    for item, line_item in ITEMS.items():
        unit, scale, number_format = UNITS[line_item.unit]
        unit = unit.replace("$", display.symbol(currency))
        items.append([display.label(item), unit])
        item_rows[item] = row_number = items.max_row
        for column, end in enumerate(years, FIRST_YEAR_COLUMN):
            target = items.cell(row_number, column)
            target.number_format = number_format
            stored = by_key.get((item, end))
            if stored is not None:
                target.value = stored.value / scale
                if stored.derivation:
                    target.comment = Comment(stored.derivation, AUTHOR)
            elif item in ZERO_IF_NEVER_REPORTED and item not in reported:
                target.value = 0
                target.comment = Comment("assumed 0 (never reported)", AUTHOR)

    sheet = book.create_sheet("Metrics")
    sheet.append([f"{ticker} metrics", "Formula", *map(display.fiscal_year, years)])
    names = [name for group in display.GROUPS.values() for name in group] + ["dupont"]
    metric_rows = {name: row_number for row_number, name in enumerate(names, 2)}
    for name in names:
        unit = f" (in {display.symbol(currency)}M)" if name in display.DOLLARS else ""
        sheet.append([display.LABELS[name], FORMULA_TEXT[name] + unit])
    for column, end in enumerate(years, FIRST_YEAR_COLUMN):
        def cell(item, years_back=0, column=column):
            if column - years_back < FIRST_YEAR_COLUMN:
                return "#REF!"  # no such year: the engine says n/a here, so this formula is never written
            return f"'{LINE_ITEMS}'!{get_column_letter(column - years_back)}{item_rows[item]}"

        formulas = _formulas(cell)
        here = get_column_letter(column)
        formulas["dupont"] = "*".join(
            f"{here}{metric_rows[factor]}" for factor in ("net_margin", "asset_turnover", "equity_multiplier")
        )
        for name in names:
            target = sheet.cell(metric_rows[name], column)
            metric = metrics[end][name]
            if metric.value is None:
                target.value = "n/a"
                target.comment = Comment(metric.reason, AUTHOR)
                continue
            target.value = f"={formulas[name]}"
            target.number_format = (
                "0.00" if name in display.MULTIPLES else "#,##0" if name in display.DOLLARS else "0.0%"
            )
            if metric.notes:
                target.comment = Comment("\n".join(metric.notes), AUTHOR)

    for worksheet in (items, sheet):
        worksheet["A1"].font = Font(bold=True)
        worksheet.freeze_panes = "C2"
        worksheet.column_dimensions["A"].width = 24
    items.column_dimensions["B"].width = 12
    sheet.column_dimensions["B"].width = 50

    output = BytesIO()
    book.save(output)
    return output.getvalue()
