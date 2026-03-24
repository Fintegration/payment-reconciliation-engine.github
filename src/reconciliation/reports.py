"""Report generation for reconciliation results."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path

from reconciliation.models import MatchedPair, ReconciliationResult, Transaction


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def generate_text_report(result: ReconciliationResult) -> str:
    """Generate a human-readable text report."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("PAYMENT RECONCILIATION REPORT")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("=" * 70)
    lines.append("")

    summary = result.summary()
    lines.append("SUMMARY")
    lines.append("-" * 40)
    for key, value in summary.items():
        lines.append(f"  {key.replace('_', ' ').title():.<30} {value}")
    lines.append(f"  {'Clean Reconciliation':.<30} {'Yes' if result.is_clean else 'No'}")
    lines.append("")

    if result.amount_mismatches:
        lines.append("AMOUNT MISMATCHES")
        lines.append("-" * 40)
        for pair in result.amount_mismatches:
            lines.append(f"  Ref: {pair.internal.reference_id}")
            lines.append(f"    Internal: {pair.internal.amount} {pair.internal.currency}")
            lines.append(f"    External: {pair.external.amount} {pair.external.currency}")
            lines.append(f"    Difference: {pair.amount_difference}")
            lines.append("")

    if result.missing_in_external:
        lines.append("MISSING IN EXTERNAL SOURCE")
        lines.append("-" * 40)
        for txn in result.missing_in_external:
            lines.append(
                f"  {txn.transaction_id} | ref={txn.reference_id} | "
                f"{txn.amount} {txn.currency} | {txn.timestamp.date()}"
            )
        lines.append("")

    if result.missing_in_internal:
        lines.append("MISSING IN INTERNAL LEDGER")
        lines.append("-" * 40)
        for txn in result.missing_in_internal:
            lines.append(
                f"  {txn.transaction_id} | ref={txn.reference_id} | "
                f"{txn.amount} {txn.currency} | {txn.timestamp.date()}"
            )
        lines.append("")

    if result.duplicates:
        lines.append("DUPLICATES DETECTED")
        lines.append("-" * 40)
        for group in result.duplicates:
            ref = group[0].reference_id
            source = group[0].source.value
            lines.append(f"  Reference {ref} ({source}): {len(group)} occurrences")
            for txn in group:
                lines.append(f"    - {txn.transaction_id} | {txn.amount} | {txn.timestamp}")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def _txn_to_dict(txn: Transaction) -> dict:
    return {
        "transaction_id": txn.transaction_id,
        "reference_id": txn.reference_id,
        "amount": str(txn.amount),
        "currency": txn.currency,
        "timestamp": txn.timestamp.isoformat(),
        "source": txn.source.value,
        "status": txn.status,
    }


def _pair_to_dict(pair: MatchedPair) -> dict:
    return {
        "internal": _txn_to_dict(pair.internal),
        "external": _txn_to_dict(pair.external),
        "status": pair.status.value,
        "amount_difference": str(pair.amount_difference),
        "discrepancies": pair.discrepancies,
    }


def generate_json_report(result: ReconciliationResult) -> str:
    """Generate a JSON report."""
    data = {
        "summary": result.summary(),
        "is_clean": result.is_clean,
        "matched": [_pair_to_dict(p) for p in result.matched],
        "amount_mismatches": [_pair_to_dict(p) for p in result.amount_mismatches],
        "missing_in_external": [_txn_to_dict(t) for t in result.missing_in_external],
        "missing_in_internal": [_txn_to_dict(t) for t in result.missing_in_internal],
        "duplicates": [
            [_txn_to_dict(t) for t in group] for group in result.duplicates
        ],
    }
    return json.dumps(data, indent=2, cls=_DecimalEncoder)


def generate_csv_report(result: ReconciliationResult) -> str:
    """Generate a CSV report of all discrepancies."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "type", "transaction_id", "reference_id", "amount", "currency",
        "timestamp", "source", "details",
    ])

    for pair in result.amount_mismatches:
        writer.writerow([
            "amount_mismatch",
            pair.internal.transaction_id,
            pair.internal.reference_id,
            str(pair.internal.amount),
            pair.internal.currency,
            pair.internal.timestamp.isoformat(),
            pair.internal.source.value,
            f"expected={pair.internal.amount} got={pair.external.amount}",
        ])

    for txn in result.missing_in_external:
        writer.writerow([
            "missing_in_external",
            txn.transaction_id,
            txn.reference_id,
            str(txn.amount),
            txn.currency,
            txn.timestamp.isoformat(),
            txn.source.value,
            "not found in external source",
        ])

    for txn in result.missing_in_internal:
        writer.writerow([
            "missing_in_internal",
            txn.transaction_id,
            txn.reference_id,
            str(txn.amount),
            txn.currency,
            txn.timestamp.isoformat(),
            txn.source.value,
            "not found in internal ledger",
        ])

    for group in result.duplicates:
        for txn in group:
            writer.writerow([
                "duplicate",
                txn.transaction_id,
                txn.reference_id,
                str(txn.amount),
                txn.currency,
                txn.timestamp.isoformat(),
                txn.source.value,
                f"{len(group)} occurrences",
            ])

    return output.getvalue()


def save_report(content: str, path: Path) -> None:
    """Write report content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
