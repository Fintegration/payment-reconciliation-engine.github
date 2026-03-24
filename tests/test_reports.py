"""Tests for report generation."""

import json
from datetime import datetime
from decimal import Decimal

from reconciliation.models import (
    MatchStatus,
    MatchedPair,
    ReconciliationResult,
    Transaction,
    TransactionSource,
)
from reconciliation.reports import generate_csv_report, generate_json_report, generate_text_report


def _txn(txn_id: str, ref: str, amount: str, source: TransactionSource) -> Transaction:
    return Transaction(
        transaction_id=txn_id,
        reference_id=ref,
        amount=Decimal(amount),
        currency="USD",
        timestamp=datetime(2026, 3, 1, 10, 0),
        source=source,
    )


def _sample_result() -> ReconciliationResult:
    int_txn = _txn("I1", "REF1", "100.00", TransactionSource.INTERNAL)
    ext_txn = _txn("E1", "REF1", "95.00", TransactionSource.STRIPE)
    mismatch = MatchedPair(
        internal=int_txn,
        external=ext_txn,
        status=MatchStatus.AMOUNT_MISMATCH,
        discrepancies=["Amount mismatch"],
    )
    missing = _txn("I2", "REF2", "200.00", TransactionSource.INTERNAL)
    return ReconciliationResult(
        amount_mismatches=[mismatch],
        missing_in_external=[missing],
    )


class TestTextReport:
    def test_contains_header(self):
        report = generate_text_report(_sample_result())
        assert "PAYMENT RECONCILIATION REPORT" in report

    def test_contains_mismatches(self):
        report = generate_text_report(_sample_result())
        assert "AMOUNT MISMATCHES" in report
        assert "REF1" in report

    def test_contains_missing(self):
        report = generate_text_report(_sample_result())
        assert "MISSING IN EXTERNAL" in report
        assert "REF2" in report


class TestJsonReport:
    def test_valid_json(self):
        report = generate_json_report(_sample_result())
        data = json.loads(report)
        assert "summary" in data
        assert data["is_clean"] is False

    def test_contains_discrepancies(self):
        report = generate_json_report(_sample_result())
        data = json.loads(report)
        assert len(data["amount_mismatches"]) == 1
        assert len(data["missing_in_external"]) == 1


class TestCsvReport:
    def test_has_header(self):
        report = generate_csv_report(_sample_result())
        lines = report.strip().split("\n")
        assert "type" in lines[0]
        assert "transaction_id" in lines[0]

    def test_has_rows(self):
        report = generate_csv_report(_sample_result())
        lines = report.strip().split("\n")
        # header + 1 mismatch + 1 missing = 3
        assert len(lines) == 3
