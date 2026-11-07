# Financial foundation

InvoiceFlow 2.0 includes a deliberately conservative financial foundation. Invoice records become financial transactions only when the user or an import explicitly classifies them as `sale`, `purchase`, `expense`, `collection` or `payment`.

An invoice is not treated as cash received, and a purchase invoice is not treated as a cash payment. Summaries are marked estimated and explain that inventory movements, opening balances, collections, payments and operating expenses require additional records.

Budget variance calculations are available as a backend service. Full accounting statements, payroll, inventory balances, multi-business permissions, bank integrations and statutory GST filing are not shipped yet.
