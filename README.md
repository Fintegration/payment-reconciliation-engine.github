# Payment Reconciliation Engine

Match internal transactions against Stripe, Razorpay & bank statements. Detect missing, duplicate, and mismatched payments.

## Features

- **Multi-source reconciliation** — match internal ledger against Stripe, Razorpay, and bank statement exports
- **Missing transaction detection** — find payments present in one source but absent from another
- **Duplicate detection** — identify duplicate charges within any source by reference ID and amount
- **Amount mismatch detection** — flag transactions where amounts differ between sources (with configurable tolerance)
- **Date mismatch detection** — detect timing discrepancies beyond a configurable threshold
- **Multiple report formats** — text, JSON, and CSV output

## Installation

```bash
pip install -e .
```

## Usage

### CLI

```bash
reconcile \
  --internal ledger.csv \
  --stripe stripe_export.csv \
  --razorpay razorpay_export.csv \
  --bank bank_statement.csv \
  --amount-tolerance 0.50 \
  --date-tolerance-days 2 \
  --format text
```

### Python API

```python
from decimal import Decimal
from reconciliation import ReconciliationEngine, TransactionSource

engine = ReconciliationEngine(amount_tolerance=Decimal("0.50"))
engine.load_internal("ledger.csv")
engine.load_external("stripe_export.csv", TransactionSource.STRIPE)

result = engine.reconcile()
print(result.summary())
# {'matched': 8, 'missing_in_external': 1, 'missing_in_internal': 2, 'duplicates': 0, 'amount_mismatches': 1}
```

## CSV Formats

### Internal Ledger
```
transaction_id, reference_id, amount, currency, timestamp, status
```

### Stripe Export
```
id, payment_intent, amount (cents), currency, created, status
```

### Razorpay Export
```
payment_id, order_id, amount (paise), currency, created_at, status
```

### Bank Statement
```
txn_ref, reference, amount, currency, date, type
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```
