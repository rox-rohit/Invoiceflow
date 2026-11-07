# Backup and restore

InvoiceFlow stores its local history at:

`%LOCALAPPDATA%\InvoiceFlow\history.db`

Close InvoiceFlow before copying the database manually. Keep a dated copy of `history.db` in a private location. The engine also exposes SQLite-consistent backup and restore methods used by automated tests.

Restoring replaces the target database. Keep the existing file as a safety copy before restoring. Invoice PDFs are not copied into the database, so source PDFs should be backed up separately.
