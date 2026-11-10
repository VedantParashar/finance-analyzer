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
            "net_income",
            (
                "NetIncomeLoss",
                "ProfitLoss",  # last resort: includes the minority interest's share of profit
            ),
            "USD",
            "flow",
        ),
        LineItem("diluted_eps", ("EarningsPerShareDiluted",), "USD/shares", "flow"),
        LineItem("total_assets", ("Assets",), "USD", "instant"),
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
