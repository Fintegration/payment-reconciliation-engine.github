"""Core reconciliation engine that orchestrates matching across sources."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from reconciliation.matchers import TransactionMatcher, find_duplicates
from reconciliation.models import (
    MatchStatus,
    ReconciliationResult,
    Transaction,
    TransactionSource,
)
from reconciliation.parsers import load_transactions


class ReconciliationEngine:
    """Reconcile internal transactions against one or more external sources.

    Usage:
        engine = ReconciliationEngine()
        engine.load_internal("ledger.csv")
        engine.load_external("stripe_export.csv", TransactionSource.STRIPE)
        result = engine.reconcile()
    """

    def __init__(
        self,
        amount_tolerance: Decimal = Decimal("0.00"),
        date_tolerance: timedelta = timedelta(days=1),
    ) -> None:
        self.amount_tolerance = amount_tolerance
        self.date_tolerance = date_tolerance
        self._internal: list[Transaction] = []
        self._external: dict[TransactionSource, list[Transaction]] = {}

    def load_internal(self, path: str | Path) -> int:
        """Load internal ledger transactions from CSV. Returns count loaded."""
        self._internal = load_transactions(Path(path), TransactionSource.INTERNAL)
        return len(self._internal)

    def load_external(self, path: str | Path, source: TransactionSource) -> int:
        """Load external provider transactions from CSV. Returns count loaded."""
        if source == TransactionSource.INTERNAL:
            raise ValueError("Use load_internal() for internal transactions")
        txns = load_transactions(Path(path), source)
        self._external[source] = txns
        return len(txns)

    def add_internal_transactions(self, transactions: list[Transaction]) -> None:
        """Add pre-parsed internal transactions."""
        self._internal.extend(transactions)

    def add_external_transactions(
        self, transactions: list[Transaction], source: TransactionSource
    ) -> None:
        """Add pre-parsed external transactions."""
        self._external.setdefault(source, []).extend(transactions)

    def reconcile(self) -> ReconciliationResult:
        """Run reconciliation across all loaded sources.

        Matches internal transactions against each external source, detects
        duplicates within each source, and compiles all discrepancies.
        """
        all_external = []
        for txns in self._external.values():
            all_external.extend(txns)

        matcher = TransactionMatcher(
            amount_tolerance=self.amount_tolerance,
            date_tolerance=self.date_tolerance,
        )

        matched_pairs, unmatched_internal, unmatched_external = matcher.match(
            self._internal, all_external
        )

        exact_matches = [p for p in matched_pairs if p.status == MatchStatus.MATCHED]
        amount_mismatches = [
            p for p in matched_pairs if p.status != MatchStatus.MATCHED
        ]

        # Detect duplicates in each source
        all_duplicates: list[list[Transaction]] = []
        all_duplicates.extend(find_duplicates(self._internal))
        for txns in self._external.values():
            all_duplicates.extend(find_duplicates(txns))

        return ReconciliationResult(
            matched=exact_matches,
            missing_in_external=unmatched_internal,
            missing_in_internal=unmatched_external,
            duplicates=all_duplicates,
            amount_mismatches=amount_mismatches,
        )
