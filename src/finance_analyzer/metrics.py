"""The SPEC's ratios and DuPont breakdown, year by year, from one company's stored line items.

Pure functions: they take rows (as returned by store.get_company) and do no I/O.
Ratios are fractions (0.276 = 27.6%), interest coverage is a multiple, free cash flow is in dollars.
"""

from collections.abc import Callable, Iterable
from datetime import date
from typing import NamedTuple

from finance_analyzer.store import StoredLineItem

# Absent can mean "the company has none" for these, but only if it never reports them.
ZERO_IF_NEVER_REPORTED = {"inventory", "short_term_debt", "long_term_debt", "short_term_investments"}
UNUSUAL_TAX_RATE = 0.5  # above this (or below zero), ROIC is still calculated but flagged


class Metric(NamedTuple):
    value: float | None  # None when it can't be calculated
    inputs: dict[str, float]  # every number used, for showing the formula filled in
    reason: str = ""  # why value is None
    notes: tuple[str, ...] = ()  # caveats that didn't stop the calculation


class _CannotCalculate(Exception):
    """Raised by a formula when it can't produce a meaningful value; the message is the reason."""


class _Inputs:
    """Looks up one fiscal year's line items for a formula, recording what was used."""

    def __init__(self, rows: dict[tuple[str, date], StoredLineItem], reported: set[str], years: list[date], end: date):
        self._rows, self._reported, self._years, self._end = rows, reported, years, end
        self.used: dict[str, float] = {}
        self.notes: list[str] = []

    def _year(self, years_back: int) -> date:
        """The fiscal year end `years_back` years earlier, only if every year in between is stored."""
        index = self._years.index(self._end)
        for step in range(years_back):
            earlier = index - step - 1
            if earlier < 0 or not 355 <= (self._years[earlier + 1] - self._years[earlier]).days <= 375:
                label = "the prior fiscal year" if years_back == 1 else f"{years_back} consecutive prior years"
                raise _CannotCalculate(f"needs {label}")
        return self._years[index - years_back]

    def get(self, item: str, years_back: int = 0) -> float:
        end = self._year(years_back)
        key = item if years_back == 0 else f"{item} (FY{end.year})"
        row = self._rows.get((item, end))
        if row is None:
            if item in ZERO_IF_NEVER_REPORTED and item not in self._reported:
                self.used[key] = 0
                self.note(f"{item} assumed 0 (never reported)")
                return 0
            raise _CannotCalculate(f"{item} not reported for FY{end.year}")
        self.used[key] = row.value
        if row.derivation:
            self.note(f"{key}: {row.derivation}")
        return row.value

    def average(self, item: str) -> float:
        value = (self.get(item) + self.get(item, 1)) / 2
        self.used[f"average {item}"] = value
        return value

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)


def _divide(numerator: float, denominator: float, name: str) -> float:
    if denominator <= 0:
        raise _CannotCalculate(f"{name} is zero or negative")
    return numerator / denominator


def _yoy(m: _Inputs, item: str) -> float:
    base = m.get(item, 1)
    if base <= 0:
        raise _CannotCalculate(f"prior-year {item} is zero or negative, so growth isn't meaningful")
    return m.get(item) / base - 1


def _cagr_3y(m: _Inputs, item: str) -> float:
    current, base = m.get(item), m.get(item, 3)
    if current <= 0 or base <= 0:
        raise _CannotCalculate(f"{item} must be positive now and 3 years earlier for a growth rate")
    return (current / base) ** (1 / 3) - 1


def _net_margin(m: _Inputs) -> float:
    return _divide(m.get("net_income"), m.get("revenue"), "revenue")


def _asset_turnover(m: _Inputs) -> float:
    return _divide(m.get("revenue"), m.average("total_assets"), "average total assets")


def _equity_multiplier(m: _Inputs) -> float:
    return _divide(m.average("total_assets"), m.average("shareholders_equity"), "average shareholders' equity")


def _invested_capital(m: _Inputs, years_back: int) -> float:
    value = (
        m.get("short_term_debt", years_back)
        + m.get("long_term_debt", years_back)
        + m.get("total_equity", years_back)
        - m.get("cash", years_back)
        - m.get("short_term_investments", years_back)
    )
    m.used["invested capital" if years_back == 0 else "invested capital (prior year)"] = value
    return value


def _roic(m: _Inputs) -> float:
    tax_rate = _divide(m.get("income_tax"), m.get("pretax_income"), "pretax income")
    m.used["tax rate"] = tax_rate
    if not 0 <= tax_rate <= UNUSUAL_TAX_RATE:
        m.note(f"tax rate of {tax_rate:.1%} is unusual, so ROIC may be distorted")
    average_invested = (_invested_capital(m, 0) + _invested_capital(m, 1)) / 2
    m.used["average invested capital"] = average_invested
    return _divide(m.get("operating_income") * (1 - tax_rate), average_invested, "average invested capital")


def _total_debt(m: _Inputs) -> float:
    return m.get("short_term_debt") + m.get("long_term_debt")


def _free_cash_flow(m: _Inputs) -> float:
    return m.get("operating_cash_flow") - m.get("capital_expenditure")


def _dupont(m: _Inputs) -> float:
    factors = {
        "net margin": _net_margin(m),
        "asset turnover": _asset_turnover(m),
        "equity multiplier": _equity_multiplier(m),
    }
    m.used.update(factors)
    return factors["net margin"] * factors["asset turnover"] * factors["equity multiplier"]


FORMULAS: dict[str, Callable[[_Inputs], float]] = {
    "gross_margin": lambda m: _divide(m.get("revenue") - m.get("cost_of_revenue"), m.get("revenue"), "revenue"),
    "operating_margin": lambda m: _divide(m.get("operating_income"), m.get("revenue"), "revenue"),
    "net_margin": _net_margin,
    "roe": lambda m: _divide(m.get("net_income"), m.average("shareholders_equity"), "average shareholders' equity"),
    "roa": lambda m: _divide(m.get("net_income"), m.average("total_assets"), "average total assets"),
    "roic": _roic,
    "current_ratio": lambda m: _divide(m.get("current_assets"), m.get("current_liabilities"), "current liabilities"),
    "quick_ratio": lambda m: _divide(
        m.get("current_assets") - m.get("inventory"), m.get("current_liabilities"), "current liabilities"
    ),
    "debt_to_equity": lambda m: _divide(_total_debt(m), m.get("shareholders_equity"), "shareholders' equity"),
    "interest_coverage": lambda m: _divide(m.get("operating_income"), m.get("interest_expense"), "interest expense"),
    "asset_turnover": _asset_turnover,
    "free_cash_flow": _free_cash_flow,
    "fcf_margin": lambda m: _divide(_free_cash_flow(m), m.get("revenue"), "revenue"),
    "revenue_growth": lambda m: _yoy(m, "revenue"),
    "revenue_cagr_3y": lambda m: _cagr_3y(m, "revenue"),
    "eps_growth": lambda m: _yoy(m, "diluted_eps"),
    "eps_cagr_3y": lambda m: _cagr_3y(m, "diluted_eps"),
    "equity_multiplier": _equity_multiplier,
    # ROE = net margin × asset turnover × equity multiplier; the three factors are in inputs.
    "dupont": _dupont,
}

def _enterprise_value(m: _Inputs, market_cap: float) -> float:
    value = market_cap + _total_debt(m) - m.get("cash") - m.get("short_term_investments")
    m.used["enterprise value"] = value
    return value


# Valuation: today's market cap (from outside the filings) against the latest fiscal year's figures.
PRICE_FORMULAS: dict[str, Callable[[_Inputs, float], float]] = {
    "market_cap": lambda m, cap: cap,
    # Market cap ÷ net income rather than price ÷ EPS: the same ratio, but a stock split after the
    # year-end changes the price and not the stored EPS, while market cap is unaffected.
    "pe": lambda m, cap: _divide(cap, m.get("net_income"), "net income"),
    "pb": lambda m, cap: _divide(cap, m.get("shareholders_equity"), "shareholders' equity"),
    "ev_ebit": lambda m, cap: _divide(_enterprise_value(m, cap), m.get("operating_income"), "operating income"),
    "fcf_yield": lambda m, cap: _free_cash_flow(m) / cap,
}

# The same formulas in words, for showing next to the numbers in Metric.inputs.
FORMULA_TEXT = {
    "gross_margin": "(revenue − cost of revenue) ÷ revenue",
    "operating_margin": "operating income ÷ revenue",
    "net_margin": "net income ÷ revenue",
    "roe": "net income ÷ average shareholders' equity",
    "roa": "net income ÷ average total assets",
    "roic": "operating income × (1 − tax rate) ÷ average invested capital, where tax rate = income tax ÷ "
    "pretax income and invested capital = short-term debt + long-term debt + total equity − cash − "
    "short-term investments",
    "current_ratio": "current assets ÷ current liabilities",
    "quick_ratio": "(current assets − inventory) ÷ current liabilities",
    "debt_to_equity": "(short-term debt + long-term debt) ÷ shareholders' equity",
    "interest_coverage": "operating income ÷ interest expense",
    "asset_turnover": "revenue ÷ average total assets",
    "free_cash_flow": "operating cash flow − capital expenditure",
    "fcf_margin": "(operating cash flow − capital expenditure) ÷ revenue",
    "revenue_growth": "revenue ÷ prior-year revenue − 1",
    "revenue_cagr_3y": "(revenue ÷ revenue 3 years earlier)^(1/3) − 1",
    "eps_growth": "diluted EPS ÷ prior-year diluted EPS − 1",
    "eps_cagr_3y": "(diluted EPS ÷ diluted EPS 3 years earlier)^(1/3) − 1",
    "equity_multiplier": "average total assets ÷ average shareholders' equity",
    "dupont": "net margin × asset turnover × equity multiplier (= ROE)",
    "market_cap": "share price × shares outstanding (from Yahoo Finance)",
    "pe": "market cap ÷ net income (the same as share price ÷ earnings per share)",
    "pb": "market cap ÷ shareholders' equity",
    "ev_ebit": "enterprise value ÷ operating income, where enterprise value = market cap + short-term debt + "
    "long-term debt − cash − short-term investments",
    "fcf_yield": "(operating cash flow − capital expenditure) ÷ market cap",
}


def company_metrics(rows: Iterable[StoredLineItem]) -> dict[date, dict[str, Metric]]:
    """Every metric for every fiscal year in one company's rows, oldest year first."""
    rows = list(rows)
    by_key = {(row.item, row.fiscal_year_end): row for row in rows}
    reported = {row.item for row in rows}
    years = sorted({row.fiscal_year_end for row in rows})

    results: dict[date, dict[str, Metric]] = {}
    for end in years:
        results[end] = {}
        for name, formula in FORMULAS.items():
            inputs = _Inputs(by_key, reported, years, end)
            results[end][name] = _run(lambda: formula(inputs), inputs)
    return results


def _run(calculate: Callable[[], float], inputs: _Inputs) -> Metric:
    try:
        value, reason = calculate(), ""
    except _CannotCalculate as error:
        value, reason = None, str(error)
    return Metric(value, inputs.used, reason, tuple(inputs.notes))


def price_metrics(
    rows: Iterable[StoredLineItem], market_cap: float | None, per_dollar: float | None = None
) -> dict[str, Metric]:
    """The valuation metrics for the latest fiscal year in the rows; all unavailable without a market cap.

    market_cap is in US dollars. When the statements aren't, it's converted into their currency at
    per_dollar (how much of that currency one dollar buys) before any ratio is taken.
    """
    if market_cap is None:
        return {name: Metric(None, {}, "share price unavailable") for name in PRICE_FORMULAS}
    rows = list(rows)
    by_key = {(row.item, row.fiscal_year_end): row for row in rows}
    years = sorted({row.fiscal_year_end for row in rows})
    currency = next((row.unit.split("/")[0] for row in rows if row.unit != "shares"), "USD")
    results = {}
    for name, formula in PRICE_FORMULAS.items():
        inputs = _Inputs(by_key, {row.item for row in rows}, years, years[-1])
        if currency == "USD":
            inputs.used["market cap"] = cap = market_cap
        elif name == "market_cap":  # stays in dollars, as Yahoo reports it
            inputs.used["market cap in US dollars"] = cap = market_cap
        elif per_dollar is None:
            # Dividing dollars by euros or yen would give a meaningless number.
            reason = f"no exchange rate from US dollars to {currency}, the currency of the statements"
            results[name] = Metric(None, {"market cap in US dollars": market_cap}, reason)
            continue
        else:
            cap = market_cap * per_dollar
            inputs.used.update({"market cap in US dollars": market_cap, f"{currency} per US dollar": per_dollar})
            inputs.used["market cap"] = cap
        results[name] = _run(lambda: formula(inputs, cap), inputs)
    return results
