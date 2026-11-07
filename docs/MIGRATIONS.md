# Database migrations

The application database is stored at `%LOCALAPPDATA%\InvoiceFlow\history.db`, outside the installation directory.

InvoiceFlow 2.1 creates a `schema_migrations` table and applies the financial-foundation migration transactionally. It adds `businesses`, `financial_transactions`, `transaction_audit` and `budgets` without deleting or rewriting the legacy invoice `records` or correction-history tables.

Before an upgrade, use the application's backup function or copy the database while InvoiceFlow is closed. If a migration is interrupted, restore the backup and rerun the application; the migration is idempotent and records its version only after the schema has been created successfully.

The new ledger is intentionally additive. Existing invoice records remain available and can be linked to explicit proposed ledger transactions for user verification.
