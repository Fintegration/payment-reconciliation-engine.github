"""Tests for transaction matching logic."""

from datetime import datetime, timedelta
from decimal import Decimal

from reconciliation.matchers import TransactionMatcher, find_duplicates
from reconciliation.models import MatchStatus, Transaction, TransactionSource


def _txn(
    txn_id: str,
    ref_id: str,
    amount: str,
    source: TransactionSource,
    ts: datetime | None = None,
) -> Transaction:
    return Transaction(
        transaction_id=txn_id,
        reference_id=ref_id,
        amount=Decimal(amount),
        currency="USD",
        timestamp=ts or datetime(2026, 3, 1, 10, 0),
        source=source,
    )


class TestTransactionMatcher:
    def test_exact_match(self):
        internal = [_txn("I1", "REF1", "100.00", TransactionSource.INTERNAL)]
        external = [_txn("E1", "REF1", "100.00", TransactionSource.STRIPE)]

        matcher = TransactionMatcher()
        matched, unmatched_int, unmatched_ext = matcher.match(internal, external)

        assert len(matched) == 1
        assert matched[0].status == MatchStatus.MATCHED
        assert len(unmatched_int) == 0
        assert len(unmatched_ext) == 0

    def test_missing_in_external(self):
        internal = [
            _txn("I1", "REF1", "100.00", TransactionSource.INTERNAL),
            _txn("I2", "REF2", "200.00", TransactionSource.INTERNAL),
        ]
        external = [_txn("E1", "REF1", "100.00", TransactionSource.STRIPE)]

        matcher = TransactionMatcher()
        matched, unmatched_int, unmatched_ext = matcher.match(internal, external)

        assert len(matched) == 1
        assert len(unmatched_int) == 1
        assert unmatched_int[0].reference_id == "REF2"

    def test_missing_in_internal(self):
        internal = [_txn("I1", "REF1", "100.00", TransactionSource.INTERNAL)]
        external = [
            _txn("E1", "REF1", "100.00", TransactionSource.STRIPE),
            _txn("E2", "REF2", "200.00", TransactionSource.STRIPE),
        ]

        matcher = TransactionMatcher()
        matched, unmatched_int, unmatched_ext = matcher.match(internal, external)

        assert len(matched) == 1
        assert len(unmatched_ext) == 1
        assert unmatched_ext[0].reference_id == "REF2"

    def test_amount_mismatch(self):
        internal = [_txn("I1", "REF1", "100.00", TransactionSource.INTERNAL)]
        external = [_txn("E1", "REF1", "95.00", TransactionSource.STRIPE)]

        matcher = TransactionMatcher(amount_tolerance=Decimal("0.00"))
        matched, _, _ = matcher.match(internal, external)

        assert len(matched) == 1
        assert matched[0].status == MatchStatus.AMOUNT_MISMATCH

    def test_amount_within_tolerance(self):
        internal = [_txn("I1", "REF1", "100.00", TransactionSource.INTERNAL)]
        external = [_txn("E1", "REF1", "99.50", TransactionSource.STRIPE)]

        matcher = TransactionMatcher(amount_tolerance=Decimal("1.00"))
        matched, _, _ = matcher.match(internal, external)

        assert len(matched) == 1
        assert matched[0].status == MatchStatus.MATCHED

    def test_date_mismatch(self):
        ts1 = datetime(2026, 3, 1, 10, 0)
        ts2 = datetime(2026, 3, 5, 10, 0)
        internal = [_txn("I1", "REF1", "100.00", TransactionSource.INTERNAL, ts=ts1)]
        external = [_txn("E1", "REF1", "100.00", TransactionSource.STRIPE, ts=ts2)]

        matcher = TransactionMatcher(date_tolerance=timedelta(days=1))
        matched, _, _ = matcher.match(internal, external)

        assert len(matched) == 1
        assert matched[0].status == MatchStatus.DATE_MISMATCH

    def test_empty_inputs(self):
        matcher = TransactionMatcher()
        matched, unmatched_int, unmatched_ext = matcher.match([], [])
        assert matched == []
        assert unmatched_int == []
        assert unmatched_ext == []


class TestFindDuplicates:
    def test_no_duplicates(self):
        txns = [
            _txn("T1", "REF1", "100.00", TransactionSource.STRIPE),
            _txn("T2", "REF2", "200.00", TransactionSource.STRIPE),
        ]
        assert find_duplicates(txns) == []

    def test_detects_duplicates(self):
        txns = [
            _txn("T1", "REF1", "100.00", TransactionSource.STRIPE),
            _txn("T2", "REF1", "100.00", TransactionSource.STRIPE),
            _txn("T3", "REF2", "200.00", TransactionSource.STRIPE),
        ]
        dupes = find_duplicates(txns)
        assert len(dupes) == 1
        assert len(dupes[0]) == 2

    def test_different_amounts_not_duplicate(self):
        txns = [
            _txn("T1", "REF1", "100.00", TransactionSource.STRIPE),
            _txn("T2", "REF1", "200.00", TransactionSource.STRIPE),
        ]
        assert find_duplicates(txns) == []
