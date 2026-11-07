# InvoiceFlow 3.0.0 UI Acceptance

This document records acceptance evidence for the 3.0 product-experience foundation. It is not a claim that every requested redesign phase is complete.

| Area | Result | Notes |
|---|---|---|
| Native PySide6 shell | PASS | Existing stacked-page architecture preserved. |
| Approved IF branding | PASS | Existing PNG/ICO assets remain in use. |
| Central design tokens | PASS | Brand, surface, text, state and spacing tokens are defined centrally. |
| Collapsible sidebar | PASS | Expand/collapse state persists through `app_settings`; collapsed navigation retains tooltips. |
| Light theme | PASS | Existing GUI regression coverage passes. |
| Dark theme | PARTIAL | Central stylesheet and contrast improvements are present; every page still needs manual visual acceptance. |
| Dashboard redesign | PARTIAL | Existing verified KPI/chart dashboard remains functional; premium 3.0 hierarchy and drill-down work remain. |
| Onboarding wizard | PARTIAL | Existing onboarding persists settings but is not yet a multi-step resumable wizard. |
| Independent import centre | PARTIAL | Existing import workflows and provenance remain functional; unified workflow coverage remains. |
| Clean Windows package | NOT TESTED | Existing 2.5.1 installer was tested on the development host, not a clean VM. |
| 3.0.0 installer smoke test | PASS | Custom isolated install launched from `C:\Windows\Temp`; database was created under isolated `%LOCALAPPDATA%`; uninstall removed binaries and preserved the database. |
| 3.0.0 package artifact | PASS | `dist\InvoiceFlow_3.0.0\InvoiceFlow_Setup_3.0.0.exe`; SHA256 `8C068F22582B244ADB7D2A36ABAEE7EE83BAA7ADE7BC6A5524D616A988B6935B`. |
| Visual screenshot capture | PASS WITH LIMITATION | 24 light/dark screenshots captured under `data\ui_redesign_3.0\` for Dashboard, Analytics, Transactions, Invoice upload, Imports and Settings at 1280x875 and 900x680. The offscreen Qt environment exposes no installed font families, so glyph rendering in these automated captures is not a valid Windows typography acceptance signal. |

Required remaining visual checks before 3.0 release: inspect on a real Windows desktop at 1280x875, 1024x768 and 900x680 in light, dark and system modes, including charts, dialogs, tables and onboarding.
