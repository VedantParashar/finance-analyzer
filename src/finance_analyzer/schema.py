"""The standard schema: which XBRL tags feed each line item."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LineItem:
    name: str
    tags: tuple[str, ...]  # priority order: decides ties between tags filed on the same day
    unit: str  # the key under a tag's "units" in the SEC data
    period_type: Literal["flow", "instant"]  # flow = over a year, instant = on one date


ITEMS = {
    item.name: item
    for item in (
        # Income statement
        LineItem(
            "revenue",
            (
                # Companies moved to the first tag with the ASC 606 revenue standard (2018).
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "SalesRevenueNet",
                "SalesRevenueGoodsNet",  # last resort: goods only for companies that also sell services
            ),
            "USD",
            "flow",
        ),
        LineItem(
            "cost_of_revenue",
            ("CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold"),
            "USD",
            "flow",
        ),
        LineItem("operating_income", ("OperatingIncomeLoss",), "USD", "flow"),
        LineItem(
            "interest_expense",
            # Many companies moved to the "Nonoperating" tag in 2022-23.
            ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"),
            "USD",
            "flow",
        ),
        LineItem(
            "pretax_income",
            (
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            ),
            "USD",
            "flow",
        ),
        LineItem("income_tax", ("IncomeTaxExpenseBenefit",), "USD", "flow"),
        LineItem(
            "net_income",
            (
                "NetIncomeLoss",
                "ProfitLoss",  # last resort: includes the minority interest's share of profit
            ),
            "USD",
            "flow",
        ),
        LineItem("diluted_eps", ("EarningsPerShareDiluted",), "USD/shares", "flow"),
        # Weighted average over the year, as used for EPS, not the count on the last day.
        LineItem("diluted_shares", ("WeightedAverageNumberOfDilutedSharesOutstanding",), "shares", "flow"),
        # Balance sheet
        LineItem("cash", ("CashAndCashEquivalentsAtCarryingValue",), "USD", "instant"),
        LineItem("short_term_investments", ("MarketableSecuritiesCurrent",), "USD", "instant"),
        LineItem("inventory", ("InventoryNet",), "USD", "instant"),
        LineItem("current_assets", ("AssetsCurrent",), "USD", "instant"),
        LineItem("total_assets", ("Assets",), "USD", "instant"),
        LineItem(
            # The reported total; when it's missing we add up SHORT_TERM_BORROWINGS (or its parts)
            # and CURRENT_MATURITIES_OF_LONG_TERM_DEBT.
            "short_term_debt",
            ("DebtCurrent",),
            "USD",
            "instant",
        ),
        LineItem("current_liabilities", ("LiabilitiesCurrent",), "USD", "instant"),
        LineItem(
            # LONG_TERM_DEBT_LAST_RESORT fills years where neither tag is reported.
            "long_term_debt",
            ("LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"),
            "USD",
            "instant",
        ),
        LineItem("total_liabilities", ("Liabilities",), "USD", "instant"),
        LineItem(
            # Sits between liabilities and equity: stakes or notes that may have to be paid out in cash.
            # Usually the sum of TEMPORARY_EQUITY_PARTS; this tag is only used when neither part is
            # reported, because it doesn't always include both (Tesla FY2020).
            "temporary_equity",
            ("TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",),
            "USD",
            "instant",
        ),
        LineItem(
            # Includes minority owners, so that assets = liabilities + equity holds.
            "total_equity",
            (
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                "StockholdersEquity",
            ),
            "USD",
            "instant",
        ),
        # Parent company's owners only: the right denominator for ROE.
        LineItem("shareholders_equity", ("StockholdersEquity",), "USD", "instant"),
        # Cash flow statement
        LineItem(
            "operating_cash_flow",
            (
                "NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            ),
            "USD",
            "flow",
        ),
        LineItem(
            "capital_expenditure",
            ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
            "USD",
            "flow",
        ),
    )
}

# Not one of the standard items: the balance sheet's bottom line, used to derive
# liabilities for companies that don't report them and to balance-check those companies.
LIABILITIES_AND_EQUITY = LineItem(
    "liabilities_and_equity", ("LiabilitiesAndStockholdersEquity",), "USD", "instant"
)

# The two parts that add up to temporary equity.
TEMPORARY_EQUITY_PARTS = (
    LineItem(
        "redeemable_minority_interest",
        ("RedeemableNoncontrollingInterestEquityCarryingAmount",),
        "USD",
        "instant",
    ),
    LineItem(
        "parent_temporary_equity",  # e.g. convertible notes that may be settled in cash
        ("TemporaryEquityCarryingAmountAttributableToParent", "TemporaryEquityValueExcludingAdditionalPaidInCapital"),
        "USD",
        "instant",
    ),
)

# Short-term debt parts, used when DebtCurrent isn't reported.
# ShortTermBorrowings already includes the two parts after it, so it replaces them, never adds to them.
SHORT_TERM_BORROWINGS = LineItem("short-term borrowings", ("ShortTermBorrowings",), "USD", "instant")
SHORT_TERM_BORROWING_PARTS = (
    LineItem("commercial paper", ("CommercialPaper",), "USD", "instant"),
    LineItem("other short-term borrowings", ("OtherShortTermBorrowings",), "USD", "instant"),
)
CURRENT_MATURITIES_OF_LONG_TERM_DEBT = LineItem(
    "current maturities of long-term debt",
    ("LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"),
    "USD",
    "instant",
)

# Usually means total debt including the current part (Apple, KO, NVDA), but Tesla uses it for
# the non-current part only. Used only when no non-current tag is reported, and labelled as such.
LONG_TERM_DEBT_LAST_RESORT = LineItem("long_term_debt", ("LongTermDebt",), "USD", "instant")
