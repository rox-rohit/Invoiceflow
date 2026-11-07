# InvoiceFlow 2.0 intelligence status

## Shipped and tested

- Exact SHA-256 source-file identity.
- Normalized invoice identity using vendor, invoice number, date, currency and total.
- Weighted duplicate comparison with `EXACT_DUPLICATE`, `CONFIRMED_INVOICE_DUPLICATE`, `POSSIBLE_DUPLICATE` and `NOT_DUPLICATE` decisions.
- False-positive guard for identical invoice numbers from different vendors.
- Field evidence metadata: value, normalized value, heuristic confidence, method, page and supporting text.
- Historical vendor-total anomaly alerts using median absolute deviation when at least three comparable records exist.
- Correction-feedback export containing only user-verified corrections and extraction version metadata.
- Conservative financial summary foundation that distinguishes invoices from collections/payments and marks incomplete estimates.

Confidence values are explicitly marked uncalibrated because the available labeled corpus is too small. They are evidence signals for review, not statistical probability claims.

## Deferred deliberately

No trained ML classifier, OCR engine, watched-folder service or automatic model retraining is shipped in 2.0. The current four-invoice ground-truth sample is insufficient for responsible model training or calibration. Interfaces and benchmark hooks should be extended only after a privacy-reviewed, vendor-separated labeled dataset is available.
