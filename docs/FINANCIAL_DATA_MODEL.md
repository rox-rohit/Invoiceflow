# Financial data model

InvoiceFlow 2.1 keeps the existing `records` and correction-history tables intact and adds a versioned financial ledger in the same user database.

## Ledger records

`financial_transactions` stores explicit business events such as `sale`, `purchase`, `expense`, `collection`, `supplier_payment`, returns, payroll, owner movements and tax payments. Amounts and tax amounts are stored as decimal text and are calculated with Python `Decimal`, avoiding binary floating-point arithmetic.

Each record includes the business, dates, counterparty, category, currency, payment status, verification status and source record/file. `source_record_id` links a ledger proposal back to the original extracted invoice. A proposal remains `PROPOSED` until a user or trusted import verifies or rejects it.

## Reporting definitions

- Sales metrics use explicitly classified `sale` transactions.
- Purchase metrics use explicitly classified `purchase` transactions.
- Collections and payments use explicitly recorded `collection` and `payment`/`supplier_payment` transactions.
- Estimated gross profit is sales minus explicitly classified purchases. It is not definitive COGS without inventory movement and opening/closing stock.
- Estimated net profit is sales minus purchases and operating expenses. It is not a statutory accounting statement.
- Cross-currency records are excluded unless an exchange rate is supplied; the report identifies this limitation.

Reports preserve source IDs for traceability and include data-quality notes when the dataset is incomplete.
