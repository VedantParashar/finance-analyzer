import re
from io import BytesIO

import pytest
from openpyxl import load_workbook

from finance_analyzer.display import LABELS
from finance_analyzer.export import company_workbook
from finance_analyzer.metrics import company_metrics
from test_metrics import AAPL, KO, rows_from
from test_red_flags import AAPL as AAPL_FLAGS, KO as KO_FLAGS


def evaluate(book, sheet: str, formula: str) -> float:
    """Work out an exported formula in Python, following references into other cells."""

    def value(sheet_name, coordinate):
        cell = book[sheet_name][coordinate].value
        return evaluate(book, sheet_name, cell[1:]) if isinstance(cell, str) and cell.startswith("=") else cell

    expression = re.sub(r"'Line items'!([A-Z]+\d+)", lambda m: repr(value("Line items", m[1])), formula)
    expression = re.sub(r"\b([A-Z]+\d+)\b", lambda m: repr(value(sheet, m[1])), expression)
    return eval(expression.replace("^", "**"))  # only our own formulas and numbers, never user input


@pytest.mark.parametrize("data", [AAPL, KO], ids=["AAPL", "KO"])
def test_every_formula_gives_the_engines_value(data):
    rows = rows_from(data)
    metrics = company_metrics(rows)
    book = load_workbook(BytesIO(company_workbook("TEST", rows, metrics)))
    sheet = book["Metrics"]
    row_of = {cell.value: cell.row for cell in sheet["A"]}
    years = [cell.value for cell in sheet[1]][2:]

    checked = 0
    for column, end in enumerate(sorted(metrics), 3):
        assert years[column - 3] == f"FY{end.year}"
        for name, metric in metrics[end].items():
            cell = sheet.cell(row_of[LABELS[name]], column)
            if metric.value is None:
                assert cell.value == "n/a" and cell.comment.text == metric.reason, name
                continue
            if name in ("piotroski_f", "beneish_m"):  # values, with their inputs in the comment
                assert cell.value == metric.value and cell.comment.text.startswith("Calculated by the app"), name
                continue
            assert cell.value.startswith("=") and "#REF!" not in cell.value, name
            scale = 1e6 if name == "free_cash_flow" else 1  # the sheet is in $M
            assert evaluate(book, "Metrics", cell.value[1:]) * scale == pytest.approx(metric.value), (name, end)
            checked += 1
    assert checked >= 17  # every metric the latest year can calculate


def test_derivations_and_assumed_zeros_become_comments():
    rows = rows_from(KO, derivations={"short_term_debt": "short-term debt = commercial paper + other"})
    rows = [row for row in rows if row.item != "inventory"]  # never reported → assumed 0
    book = load_workbook(BytesIO(company_workbook("TEST", rows, company_metrics(rows))))
    sheet = book["Line items"]
    labels = [cell.value for cell in sheet["A"]]
    debt = sheet.cell(labels.index("Short term debt") + 1, sheet.max_column)
    inventory = sheet.cell(labels.index("Inventory") + 1, sheet.max_column)
    assert debt.comment.text == "short-term debt = commercial paper + other"
    assert inventory.value == 0 and inventory.comment.text == "assumed 0 (never reported)"


@pytest.mark.parametrize("data, column, expected", [(AAPL_FLAGS, "E", (3.2024, 9, -2.5158, -0.03384)),
                                                    (KO_FLAGS, "E", (4.5036, 7, -2.3499, 0.05550))])
def test_red_flag_scores_in_the_workbook_match_the_hand_calculations(data, column, expected):
    rows = rows_from(data)
    book = load_workbook(BytesIO(company_workbook("TEST", rows, company_metrics(rows))))
    sheet = book["Metrics"]
    row_of = {cell.value: cell.row for cell in sheet["A"]}
    z, f, m, accruals = (sheet[f"{column}{row_of[LABELS[name]]}"] for name in
                         ("altman_z", "piotroski_f", "beneish_m", "accruals_ratio"))
    assert evaluate(book, "Metrics", z.value[1:]) == pytest.approx(expected[0], abs=0.0001)
    assert evaluate(book, "Metrics", accruals.value[1:]) == pytest.approx(expected[3], abs=0.00001)
    assert f.value == expected[1] and m.value == pytest.approx(expected[2], abs=0.0001)
    assert "test 1: net income is positive: pass (1 point)" in f.comment.text
    assert "receivables index: 0." in m.comment.text and "SG&A index" in m.comment.text
