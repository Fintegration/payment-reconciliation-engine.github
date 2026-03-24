"""Tests for the reconciliation engine end-to-end."""

from pathlib import Path

from reconciliation.engine import ReconciliationEngine
from reconciliation.models import TransactionSource

FIXTURES = Path(__file__).parent / "fixtures"


class TestReconciliationEngine:
    def test_load_internal(self):
        engine = ReconciliationEngine()
        count = engine.load_internal(FIXTURES / "internal_transactions.csv")
        assert count == 10

    def test_load_stripe(self):
        engine = ReconciliationEngine()
        count = engine.load_external(
            FIXTURES / "stripe_transactions.csv", TransactionSource.STRIPE
        )
        assert count == 7

    def test_load_razorpay(self):
        engine = ReconciliationEngine()
        count = engine.load_external(
            FIXTURES / "razorpay_transactions.csv", TransactionSource.RAZORPAY
        )
        assert count == 3

    def test_load_bank(self):
        engine = ReconciliationEngine()
        count = engine.load_external(
            FIXTURES / "bank_statement.csv", TransactionSource.BANK
        )
        assert count == 3

    def test_reject_internal_as_external(self):
        engine = ReconciliationEngine()
        try:
            engine.load_external(
                FIXTURES / "internal_transactions.csv", TransactionSource.INTERNAL
            )
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_full_reconciliation(self):
        engine = ReconciliationEngine()
        engine.load_internal(FIXTURES / "internal_transactions.csv")
        engine.load_external(FIXTURES / "stripe_transactions.csv", TransactionSource.STRIPE)
        engine.load_external(FIXTURES / "razorpay_transactions.csv", TransactionSource.RAZORPAY)
        engine.load_external(FIXTURES / "bank_statement.csv", TransactionSource.BANK)

        result = engine.reconcile()

        # REF001, REF002, REF003, REF005, REF006, REF007, REF008, REF009, REF010 match
        # REF004 has amount mismatch (500.00 vs 495.00)
        assert result.total_matched >= 8
        assert len(result.amount_mismatches) >= 1

        # REF099 exists in Stripe but not internal
        assert len(result.missing_in_internal) >= 1

        # REF011 exists in bank but not internal
        ext_refs = {t.reference_id for t in result.missing_in_internal}
        assert "REF099" in ext_refs or "REF011" in ext_refs

        # Razorpay has duplicate REF008
        assert len(result.duplicates) >= 1

        assert not result.is_clean

    def test_reconciliation_summary(self):
        engine = ReconciliationEngine()
        engine.load_internal(FIXTURES / "internal_transactions.csv")
        engine.load_external(FIXTURES / "stripe_transactions.csv", TransactionSource.STRIPE)

        result = engine.reconcile()
        summary = result.summary()
        assert isinstance(summary, dict)
        assert "matched" in summary
