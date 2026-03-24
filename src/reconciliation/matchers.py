"""Matching strategies for reconciling transactions across sources."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from reconciliation.models import (
    MatchedPair,
    MatchStatus,
    Transaction,
)


class TransactionMatcher:
    """Match internal transactions against external provider transactions.

    Matching is done by reference_id. Configurable tolerances for amount and date
    allow fuzzy matching to accommodate processing delays and fee differences.
    """

    def __init__(
        self,
        amount_tolerance: Decimal = Decimal("0.00"),
        date_tolerance: timedelta = timedelta(days=1),
    ) -> None:
        self.amount_tolerance = amount_tolerance
        self.date_tolerance = date_tolerance

    def match(
        self,
        internal: list[Transaction],
        external: list[Transaction],
    ) -> tuple[list[MatchedPair], list[Transaction], list[Transaction]]:
        """Match internal transactions against external ones.

        Returns:
            Tuple of (matched_pairs, unmatched_internal, unmatched_external).
        """
        ext_by_ref: dict[str, list[Transaction]] = defaultdict(list)
        for txn in external:
            ext_by_ref[txn.reference_id].append(txn)

        matched: list[MatchedPair] = []
        unmatched_internal: list[Transaction] = []
        used_external: set[str] = set()

        for int_txn in internal:
            candidates = ext_by_ref.get(int_txn.reference_id, [])
            best_match = self._find_best_match(int_txn, candidates, used_external)

            if best_match is not None:
                ext_txn, pair = best_match
                matched.append(pair)
                used_external.add(ext_txn.transaction_id)
            else:
                unmatched_internal.append(int_txn)

        unmatched_external = [
            txn for txn in external if txn.transaction_id not in used_external
        ]

        return matched, unmatched_internal, unmatched_external

    def _find_best_match(
        self,
        int_txn: Transaction,
        candidates: list[Transaction],
        used: set[str],
    ) -> tuple[Transaction, MatchedPair] | None:
        """Find the best matching external transaction for an internal one."""
        for ext_txn in candidates:
            if ext_txn.transaction_id in used:
                continue

            discrepancies: list[str] = []
            status = MatchStatus.MATCHED

            amount_diff = abs(int_txn.amount - ext_txn.amount)
            if amount_diff > self.amount_tolerance:
                status = MatchStatus.AMOUNT_MISMATCH
                discrepancies.append(
                    f"Amount mismatch: internal={int_txn.amount}, "
                    f"external={ext_txn.amount}, diff={amount_diff}"
                )

            time_diff = abs(int_txn.timestamp - ext_txn.timestamp)
            if time_diff > self.date_tolerance:
                if status == MatchStatus.MATCHED:
                    status = MatchStatus.DATE_MISMATCH
                discrepancies.append(
                    f"Date mismatch: internal={int_txn.timestamp}, "
                    f"external={ext_txn.timestamp}, diff={time_diff}"
                )

            pair = MatchedPair(
                internal=int_txn,
                external=ext_txn,
                status=status,
                discrepancies=discrepancies,
            )
            return ext_txn, pair

        return None


def find_duplicates(transactions: list[Transaction]) -> list[list[Transaction]]:
    """Find duplicate transactions within a single source.

    Duplicates are identified by matching reference_id and amount.
    """
    groups: dict[tuple[str, Decimal], list[Transaction]] = defaultdict(list)
    for txn in transactions:
        key = (txn.reference_id, txn.amount)
        groups[key].append(txn)

    return [group for group in groups.values() if len(group) > 1]
