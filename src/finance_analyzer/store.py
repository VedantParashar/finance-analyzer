"""Save standard line items to a local DuckDB file and read them back."""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import NamedTuple

import duckdb

from finance_analyzer import parse
from finance_analyzer.edgar import fetch_company_facts
from finance_analyzer.parse import annual_line_items, company_currency
from finance_analyzer.schema import ITEMS

DB_PATH = Path("data/finance.duckdb")

CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS line_items (
        ticker VARCHAR NOT NULL,
        item VARCHAR NOT NULL,
        fiscal_year_end DATE NOT NULL,
        value DOUBLE NOT NULL,
        unit VARCHAR NOT NULL,
        accn VARCHAR NOT NULL,
        derivation VARCHAR NOT NULL,
        loaded_at TIMESTAMP NOT NULL,
        PRIMARY KEY (ticker, item, fiscal_year_end)
    )
"""


class StoredLineItem(NamedTuple):
    ticker: str
    item: str
    fiscal_year_end: date
    value: float
    unit: str
    accn: str
    derivation: str  # empty = as reported, otherwise how we calculated the value
    loaded_at: datetime


def _connect() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(DB_PATH))
    connection.execute(CREATE_TABLE)
    return connection


def load_company(ticker: str) -> int:
    """Fetch, parse and save a company, replacing its old rows. Returns the rows saved."""
    ticker = ticker.strip().upper()
    # Parse before touching the database, so a failed download can't affect saved data.
    rows = annual_line_items(ticker)
    if not rows:
        raise ValueError(f"No line items found for {ticker}, keeping any saved data")

    currency = company_currency(ticker)  # each row's unit records it: "EUR", "EUR/shares"
    loaded_at = datetime.now(UTC).replace(tzinfo=None)  # stored as UTC
    with _connect() as connection:
        connection.begin()  # leaving this block without commit() undoes everything below
        connection.execute("DELETE FROM line_items WHERE ticker = ?", [ticker])
        connection.executemany(
            "INSERT INTO line_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (ticker, r.item, r.fiscal_year_end, r.value, ITEMS[r.item].unit.replace("USD", currency), r.accn,
                 r.derivation, loaded_at)
                for r in rows
            ],
        )
        connection.commit()
    return len(rows)


def get_company(ticker: str) -> list[StoredLineItem]:
    """A company's saved rows by schema order then oldest year first; empty if never loaded."""
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM line_items WHERE ticker = ? ORDER BY list_position(?, item), fiscal_year_end",
            [ticker.strip().upper(), list(ITEMS)],
        ).fetchall()
    return [StoredLineItem(*row) for row in rows]


def trailing_twelve_months(ticker: str) -> list[StoredLineItem]:
    """Rows for the twelve months to the latest quarter end (and the same quarter in earlier years).

    Built from the SEC download each time and not saved: the database holds fiscal years only.
    """
    ticker = ticker.strip().upper()
    facts = fetch_company_facts(ticker)
    currency = parse.reporting_currency(facts)
    now = datetime.now(UTC).replace(tzinfo=None)
    return [
        StoredLineItem(ticker, r.item, date.fromisoformat(r.fiscal_year_end), r.value,
                       ITEMS[r.item].unit.replace("USD", currency), r.accn, r.derivation, now)
        for r in parse.trailing_twelve_months(facts)
    ]
