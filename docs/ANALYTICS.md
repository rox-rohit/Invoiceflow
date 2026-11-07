# Business analytics methodology

InvoiceFlow 2.3 uses one shared analytics service for the Business Overview page, charts, party pages and evidence-based insights.

## Data scope

Only transactions with `VERIFIED` status are included in the financial intelligence views. Extracted invoice records remain document records until the user explicitly approves their transaction type. Sales are separate from collections; purchases are separate from supplier payments.

## KPI definitions

- Sales: verified sales minus verified sales returns.
- Purchases: verified purchases minus verified purchase returns.
- Expenses: verified operating-expense transactions.
- Gross profit: sales minus purchases, shown as estimated because inventory movements and opening/closing stock are not represented.
- Net profit: shown only when both purchase and expense records exist, and remains explicitly estimated.
- Collections: explicit customer collection transactions.
- Payments: explicit supplier or operating payment transactions.

Missing data is not treated as zero. The dashboard displays a data-quality explanation instead.

## Periods

The application supports visual presets, custom calendar dates and configurable financial years. April–March is the default financial year. Previous-period comparisons use an equal-length preceding period.

## Insights

Insights are deterministic findings tied to source transaction IDs. They are review prompts, not fraud findings or guaranteed forecasts. Cross-currency transactions are excluded unless an exchange-rate model is supplied.
