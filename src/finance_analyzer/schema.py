"""The standard schema: which XBRL tags feed each line item."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LineItem:
    name: str
    tags: tuple[str, ...]  # priority order: decides ties between tags filed on the same day
    unit: str  # the key under a tag's "units" in the SEC data; "USD" stands for the company's own currency
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
        LineItem(
            # Marketable securities; built together with OTHER_SHORT_TERM_INVESTMENTS, which some
            # companies (KO) show as a separate balance sheet line.
            "short_term_investments",
            # The second tag is what ASML uses for its short-term deposits and securities.
            ("MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
            "USD",
            "instant",
        ),
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

# Short-term investment parts. MarketableSecurities has meant the current line wherever we've seen it
# (KO after FY2020, NVDA), but could be the total at a company that also holds long-dated securities,
# so it's only used in years with no MarketableSecuritiesNoncurrent.
MARKETABLE_SECURITIES_ANY_TERM = LineItem("marketable securities", ("MarketableSecurities",), "USD", "instant")
MARKETABLE_SECURITIES_NONCURRENT = LineItem(
    "non-current marketable securities", ("MarketableSecuritiesNoncurrent",), "USD", "instant"
)
OTHER_SHORT_TERM_INVESTMENTS = LineItem(
    "short-term investments", ("ShortTermInvestments", "OtherShortTermInvestments"), "USD", "instant"
)

# Usually means total debt including the current part (Apple, KO, NVDA), but Tesla uses it for
# the non-current part only. Used only when no non-current tag is reported, and labelled as such.
LONG_TERM_DEBT_LAST_RESORT = LineItem("long_term_debt", ("LongTermDebt",), "USD", "instant")


# The same line items for companies that report under IFRS (most foreign filers), from the `ifrs-full`
# taxonomy. Keyed by line item name; same rules as `tags`: priority order, first wins on a tie.
IFRS_TAGS: dict[str, tuple[str, ...]] = {
    # Income statement
    "revenue": ("Revenue", "RevenueFromContractsWithCustomers"),
    "cost_of_revenue": ("CostOfSales",),
    "operating_income": ("ProfitLossFromOperatingActivities",),
    # FinanceCosts is the income statement line: usually interest, but it can include other financing losses.
    # InterestExpenseOnBorrowings isn't used: at TSMC it leaves out the interest on bonds.
    "interest_expense": ("InterestExpense", "FinanceCosts"),
    "pretax_income": ("ProfitLossBeforeTax",),
    "income_tax": ("IncomeTaxExpenseContinuingOperations",),
    "net_income": ("ProfitLossAttributableToOwnersOfParent", "ProfitLoss"),
    "diluted_eps": ("DilutedEarningsLossPerShare", "DilutedEarningsLossPerShareFromContinuingOperations"),
    # The diluted count only: WeightedAverageShares is the basic count, so it isn't used.
    "diluted_shares": ("AdjustedWeightedAverageShares",),
    # Balance sheet
    "cash": ("CashAndCashEquivalents",),
    # IFRS has no "marketable securities" line; the second tag can also hold loans and derivatives.
    "short_term_investments": ("CurrentInvestments", "OtherCurrentFinancialAssets"),
    "inventory": ("Inventories",),
    "current_assets": ("CurrentAssets",),
    "total_assets": ("Assets",),
    "short_term_debt": ("CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings",),
    "current_liabilities": ("CurrentLiabilities",),
    "long_term_debt": ("LongtermBorrowings", "NoncurrentPortionOfNoncurrentBorrowings"),
    "total_liabilities": ("Liabilities",),
    "temporary_equity": (),  # a US GAAP idea; IFRS puts these amounts in liabilities
    "total_equity": ("Equity",),
    "shareholders_equity": ("EquityAttributableToOwnersOfParent",),
    # Cash flow statement
    "operating_cash_flow": ("CashFlowsFromUsedInOperatingActivities",),
    "capital_expenditure": (
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        # Last resort (SAP): also includes purchases of intangible assets.
        "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets",
    ),
    # The helper items above that have an IFRS equivalent
    "liabilities_and_equity": ("EquityAndLiabilities",),
    "short-term borrowings": ("ShorttermBorrowings",),
    "current maturities of long-term debt": ("CurrentPortionOfLongtermBorrowings",),
}
