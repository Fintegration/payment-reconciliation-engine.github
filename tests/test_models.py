"""Tests for transaction models."""

from datetime import datetime
from decimal import Decimal

from reconciliation.models import (
    MatchStatus,
    MatchedPair,
    ReconciliationResult,
    Transaction,
    TransactionSource,
)


def _make_txn(
    txn_id: str = "T1",
    ref_id: str = "REF1",
    amount: str = "100.00",
    source: TransactionSource = TransactionSource.INTERNAL,
) -> Transaction:
    return Transaction(
        transaction_id=txn_id,
        reference_id=ref_id,
        amount=Decimal(amount),
        currency="USD",
        timestamp=datetime(2026, 3, 1, 10, 0),
        source=source,
    )


class TestTransaction:
    def test_amount_in_minor_units(self):
        txn = _make_txn(amount="99.99")
        assert txn.amount_in_minor_units() == 9999

    def test_frozen(self):
        txn = _make_txn()
        try:
            txn.amount = Decimal("200")  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass


class TestReconciliationResult:
    def test_clean_result(self):
        result = ReconciliationResult()
        assert result.is_clean
        assert result.total_discrepancies == 0

    def test_summary_counts(self):
        int_txn = _make_txn(source=TransactionSource.INTERNAL)
        ext_txn = _make_txn(txn_id="E1", source=TransactionSource.STRIPE)
        pair = MatchedPair(
            internal=int_txn,
            external=ext_txn,
            status=MatchStatus.MATCHED,
        )
        result = ReconciliationResult(
            matched=[pair],
            missing_in_external=[_make_txn(txn_id="M1")],
        )
        assert result.total_matched == 1
        assert result.total_discrepancies == 1
        assert not result.is_clean

    def test_summary_dict(self):
        result = ReconciliationResult()
        s = result.summary()
        assert set(s.keys()) == {
            "matched",
            "missing_in_external",
            "missing_in_internal",
            "duplicates",
            "amount_mismatches",
        }


class TestMatchedPair:
    def test_amount_difference(self):
        int_txn = _make_txn(amount="100.00", source=TransactionSource.INTERNAL)
        ext_txn = _make_txn(amount="95.00", txn_id="E1", source=TransactionSource.STRIPE)
        pair = MatchedPair(
            internal=int_txn,
            external=ext_txn,
            status=MatchStatus.AMOUNT_MISMATCH,
        )
        assert pair.amount_difference == Decimal("5.00")
