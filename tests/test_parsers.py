"""Tests for CSV parsers."""

from decimal import Decimal
from pathlib import Path

from reconciliation.models import TransactionSource
from reconciliation.parsers import (
    parse_bank_statement,
    parse_internal,
    parse_razorpay,
    parse_stripe,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseInternal:
    def test_loads_all_rows(self):
        txns = parse_internal(FIXTURES / "internal_transactions.csv")
        assert len(txns) == 10

    def test_correct_fields(self):
        txns = parse_internal(FIXTURES / "internal_transactions.csv")
        first = txns[0]
        assert first.transaction_id == "INT001"
        assert first.reference_id == "REF001"
        assert first.amount == Decimal("100.00")
        assert first.currency == "USD"
        assert first.source == TransactionSource.INTERNAL


class TestParseStripe:
    def test_loads_all_rows(self):
        txns = parse_stripe(FIXTURES / "stripe_transactions.csv")
        assert len(txns) == 7

    def test_converts_cents_to_dollars(self):
        txns = parse_stripe(FIXTURES / "stripe_transactions.csv")
        first = txns[0]
        assert first.amount == Decimal("100.00")
        assert first.source == TransactionSource.STRIPE


class TestParseRazorpay:
    def test_loads_all_rows(self):
        txns = parse_razorpay(FIXTURES / "razorpay_transactions.csv")
        assert len(txns) == 3

    def test_converts_paise_to_rupees(self):
        txns = parse_razorpay(FIXTURES / "razorpay_transactions.csv")
        first = txns[0]
        assert first.amount == Decimal("320.00")
        assert first.source == TransactionSource.RAZORPAY


class TestParseBankStatement:
    def test_loads_all_rows(self):
        txns = parse_bank_statement(FIXTURES / "bank_statement.csv")
        assert len(txns) == 3

    def test_correct_fields(self):
        txns = parse_bank_statement(FIXTURES / "bank_statement.csv")
        first = txns[0]
        assert first.transaction_id == "BNK001"
        assert first.reference_id == "REF009"
        assert first.amount == Decimal("999.99")
        assert first.source == TransactionSource.BANK
