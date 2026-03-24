"""Parsers for loading transactions from CSV files of various payment providers."""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from reconciliation.models import Transaction, TransactionSource


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_internal(path: Path) -> list[Transaction]:
    """Parse internal ledger CSV.

    Expected columns: transaction_id, reference_id, amount, currency, timestamp, status
    """
    rows = _read_csv(path)
    txns: list[Transaction] = []
    for row in rows:
        txns.append(
            Transaction(
                transaction_id=row["transaction_id"].strip(),
                reference_id=row["reference_id"].strip(),
                amount=Decimal(row["amount"].strip()),
                currency=row["currency"].strip().upper(),
                timestamp=datetime.fromisoformat(row["timestamp"].strip()),
                source=TransactionSource.INTERNAL,
                status=row.get("status", "completed").strip(),
            )
        )
    return txns


def parse_stripe(path: Path) -> list[Transaction]:
    """Parse Stripe export CSV.

    Expected columns: id, payment_intent, amount, currency, created, status
    Stripe amounts are in minor units (cents).
    """
    rows = _read_csv(path)
    txns: list[Transaction] = []
    for row in rows:
        amount_cents = int(row["amount"].strip())
        txns.append(
            Transaction(
                transaction_id=row["id"].strip(),
                reference_id=row["payment_intent"].strip(),
                amount=Decimal(amount_cents) / Decimal(100),
                currency=row["currency"].strip().upper(),
                timestamp=datetime.fromisoformat(row["created"].strip()),
                source=TransactionSource.STRIPE,
                status=row.get("status", "succeeded").strip(),
            )
        )
    return txns


def parse_razorpay(path: Path) -> list[Transaction]:
    """Parse Razorpay export CSV.

    Expected columns: payment_id, order_id, amount, currency, created_at, status
    Razorpay amounts are in minor units (paise for INR).
    """
    rows = _read_csv(path)
    txns: list[Transaction] = []
    for row in rows:
        amount_paise = int(row["amount"].strip())
        txns.append(
            Transaction(
                transaction_id=row["payment_id"].strip(),
                reference_id=row["order_id"].strip(),
                amount=Decimal(amount_paise) / Decimal(100),
                currency=row["currency"].strip().upper(),
                timestamp=datetime.fromisoformat(row["created_at"].strip()),
                source=TransactionSource.RAZORPAY,
                status=row.get("status", "captured").strip(),
            )
        )
    return txns


def parse_bank_statement(path: Path) -> list[Transaction]:
    """Parse bank statement CSV.

    Expected columns: txn_ref, reference, amount, currency, date, type
    """
    rows = _read_csv(path)
    txns: list[Transaction] = []
    for row in rows:
        txns.append(
            Transaction(
                transaction_id=row["txn_ref"].strip(),
                reference_id=row["reference"].strip(),
                amount=Decimal(row["amount"].strip()),
                currency=row["currency"].strip().upper(),
                timestamp=datetime.fromisoformat(row["date"].strip()),
                source=TransactionSource.BANK,
                status=row.get("type", "credit").strip(),
            )
        )
    return txns


PARSERS = {
    TransactionSource.INTERNAL: parse_internal,
    TransactionSource.STRIPE: parse_stripe,
    TransactionSource.RAZORPAY: parse_razorpay,
    TransactionSource.BANK: parse_bank_statement,
}


def load_transactions(path: Path, source: TransactionSource) -> list[Transaction]:
    """Load transactions from a CSV file using the appropriate parser."""
    parser = PARSERS[source]
    return parser(path)
