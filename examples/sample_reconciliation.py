"""Example: run reconciliation against Stripe, Razorpay, and bank data."""

from decimal import Decimal
from pathlib import Path

from reconciliation.engine import ReconciliationEngine
from reconciliation.models import TransactionSource
from reconciliation.reports import generate_text_report

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def main() -> None:
    engine = ReconciliationEngine(
        amount_tolerance=Decimal("0.50"),
    )

    engine.load_internal(FIXTURES / "internal_transactions.csv")
    engine.load_external(FIXTURES / "stripe_transactions.csv", TransactionSource.STRIPE)
    engine.load_external(FIXTURES / "razorpay_transactions.csv", TransactionSource.RAZORPAY)
    engine.load_external(FIXTURES / "bank_statement.csv", TransactionSource.BANK)

    result = engine.reconcile()

    print(generate_text_report(result))
    print(f"\nSummary: {result.summary()}")


if __name__ == "__main__":
    main()
