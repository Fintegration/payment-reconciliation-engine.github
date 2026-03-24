"""Command-line interface for the payment reconciliation engine."""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from reconciliation.engine import ReconciliationEngine
from reconciliation.models import TransactionSource
from reconciliation.reports import (
    generate_csv_report,
    generate_json_report,
    generate_text_report,
    save_report,
)

SOURCE_MAP = {
    "stripe": TransactionSource.STRIPE,
    "razorpay": TransactionSource.RAZORPAY,
    "bank": TransactionSource.BANK,
}

REPORT_GENERATORS = {
    "text": generate_text_report,
    "json": generate_json_report,
    "csv": generate_csv_report,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reconcile",
        description="Reconcile internal payment records against external sources.",
    )
    parser.add_argument(
        "--internal",
        required=True,
        type=Path,
        help="Path to internal ledger CSV",
    )
    parser.add_argument(
        "--stripe",
        type=Path,
        help="Path to Stripe export CSV",
    )
    parser.add_argument(
        "--razorpay",
        type=Path,
        help="Path to Razorpay export CSV",
    )
    parser.add_argument(
        "--bank",
        type=Path,
        help="Path to bank statement CSV",
    )
    parser.add_argument(
        "--amount-tolerance",
        type=Decimal,
        default=Decimal("0.00"),
        help="Maximum allowed amount difference (default: 0.00)",
    )
    parser.add_argument(
        "--date-tolerance-days",
        type=int,
        default=1,
        help="Maximum allowed date difference in days (default: 1)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Report output format (default: text)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write report to file instead of stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    engine = ReconciliationEngine(
        amount_tolerance=args.amount_tolerance,
        date_tolerance=timedelta(days=args.date_tolerance_days),
    )

    engine.load_internal(args.internal)

    sources = {
        "stripe": args.stripe,
        "razorpay": args.razorpay,
        "bank": args.bank,
    }

    loaded_any = False
    for name, path in sources.items():
        if path is not None:
            count = engine.load_external(path, SOURCE_MAP[name])
            print(f"Loaded {count} transactions from {name}", file=sys.stderr)
            loaded_any = True

    if not loaded_any:
        parser.error("At least one external source (--stripe, --razorpay, --bank) is required")

    result = engine.reconcile()
    generator = REPORT_GENERATORS[args.format]
    report = generator(result)

    if args.output:
        save_report(report, args.output)
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(report)

    return 0 if result.is_clean else 1


if __name__ == "__main__":
    sys.exit(main())
