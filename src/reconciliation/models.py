"""Data models for payment transactions and reconciliation results."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


class TransactionSource(enum.Enum):
    """Origin of a transaction record."""

    INTERNAL = "internal"
    STRIPE = "stripe"
    RAZORPAY = "razorpay"
    BANK = "bank"


class MatchStatus(enum.Enum):
    """Outcome of reconciliation for a transaction."""

    MATCHED = "matched"
    MISSING = "missing"
    DUPLICATE = "duplicate"
    AMOUNT_MISMATCH = "amount_mismatch"
    DATE_MISMATCH = "date_mismatch"


@dataclass(frozen=True)
class Transaction:
    """A single payment transaction from any source."""

    transaction_id: str
    reference_id: str
    amount: Decimal
    currency: str
    timestamp: datetime
    source: TransactionSource
    status: str = "completed"
    metadata: dict[str, Any] = field(default_factory=dict)

    def amount_in_minor_units(self) -> int:
        """Return amount in smallest currency unit (e.g. cents/paise)."""
        return int(self.amount * 100)


@dataclass
class MatchedPair:
    """A pair of transactions that have been matched together."""

    internal: Transaction
    external: Transaction
    status: MatchStatus
    discrepancies: list[str] = field(default_factory=list)

    @property
    def amount_difference(self) -> Decimal:
        return self.internal.amount - self.external.amount


@dataclass
class ReconciliationResult:
    """Full result of a reconciliation run."""

    matched: list[MatchedPair] = field(default_factory=list)
    missing_in_external: list[Transaction] = field(default_factory=list)
    missing_in_internal: list[Transaction] = field(default_factory=list)
    duplicates: list[list[Transaction]] = field(default_factory=list)
    amount_mismatches: list[MatchedPair] = field(default_factory=list)

    @property
    def total_matched(self) -> int:
        return len(self.matched)

    @property
    def total_discrepancies(self) -> int:
        return (
            len(self.missing_in_external)
            + len(self.missing_in_internal)
            + len(self.duplicates)
            + len(self.amount_mismatches)
        )

    @property
    def is_clean(self) -> bool:
        return self.total_discrepancies == 0

    def summary(self) -> dict[str, int]:
        return {
            "matched": self.total_matched,
            "missing_in_external": len(self.missing_in_external),
            "missing_in_internal": len(self.missing_in_internal),
            "duplicates": len(self.duplicates),
            "amount_mismatches": len(self.amount_mismatches),
        }
