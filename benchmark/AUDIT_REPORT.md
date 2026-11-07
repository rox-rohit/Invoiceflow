# InvoiceFlow extraction audit

Date: 2026-11-07

## Automated corpus audit

- Corpus inspected: `data/Samples of electronic invoices`
- Automated sample: first 300 PDFs in deterministic path order
- Results: 300 processed, 300 `FOUND`, 0 `ERROR`, 0 `REQUIRES_OCR`, 0 `NOT_AN_INVOICE`
- Informational issues: 1,121 line arithmetic differences
- Review status: line arithmetic differences are informational because pack/unit pricing can make quantity × rate non-comparable. They remain visible in Processing Issues.

This is not a claim of real-world accuracy for all invoice layouts.

## Manual ground-truth sample

Four real invoices were manually transcribed from their visible PDF text into `ground_truth_sample.json`. The selected files cover the common dataset template and include 1–3 line items. The benchmark runner compared invoice number, date, vendor, customer, subtotal, tax and total.

| Field | Correct | Missing | Ambiguous | Applicable | Accuracy |
|---|---:|---:|---:|---:|---:|
| Invoice number | 4 | 0 | 0 | 4 | 100% |
| Invoice date | 4 | 0 | 0 | 4 | 100% |
| Vendor name | 4 | 0 | 0 | 4 | 100% |
| Customer name | 4 | 0 | 0 | 4 | 100% |
| Subtotal | 4 | 0 | 0 | 4 | 100% |
| Tax amount | 4 | 0 | 0 | 4 | 100% |
| Grand total | 4 | 0 | 0 | 4 | 100% |

The sample is small and template-homogeneous; these measurements must not be generalized to the complete corpus or to unseen invoice templates.

## Most common prior review cause

Before calibration, all 300 sample records were `NEEDS_REVIEW` solely because 1,121 line arithmetic warnings were treated as blocking warnings. The validator now treats those as informational commercial-pricing suggestions, while missing fields, invalid dates, summary mismatches and processing errors remain review/error conditions.
