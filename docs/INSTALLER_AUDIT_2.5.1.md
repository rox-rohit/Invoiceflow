# InvoiceFlow 2.5.1 Installer Audit

This document records the 2.5.1 installer baseline. The 3.0.0 installer is documented separately in `docs/UI_ACCEPTANCE_3.0.0.md`; the same upgrade-safe data path and Inno Setup architecture are preserved.

## Configuration

- Installer technology: Inno Setup 6.
- Application package: PyInstaller onedir.
- Target architecture: 64-bit Windows 10/11.
- Installer output: `dist\InvoiceFlow_2.5.1\InvoiceFlow_Setup_2.5.1.exe` (103.96 MiB).
- Checksum output: `InvoiceFlow_Setup_2.5.1.exe.sha256`.
- Application package size: 345.07 MiB.
- Default install directory: `{autopf}\InvoiceFlow`.
- User database: `%LOCALAPPDATA%\InvoiceFlow\history.db`.
- User data is not included in `[UninstallDelete]`.

## Build status

The installer script and automated build step are present. Inno Setup 6.7.3 was installed through winget, and the installer compiled successfully.

## Validation status

| Check | Result |
|---|---|
| PyInstaller 2.5.1 onedir package | PASS — `dist\InvoiceFlow_2.5.1\InvoiceFlow` |
| Inno Setup installer compilation | PASS — `InvoiceFlow_Setup_2.5.1.exe` |
| SHA256 checksum | PASS — `DE57513B125BE47BABEAC91E76B090D6CA597B2F3A562ECB37309E26814B881B` |
| Source application tests | PASS — 44 tests |
| Targeted operational/GUI tests | PASS — 9 tests |
| Packaged executable launch from another working directory | PASS — process remained alive during smoke check |
| Custom install directory | PASS — silent smoke install |
| Installed application launch | PASS — launched with isolated `%LOCALAPPDATA%` |
| Uninstall preserving user data | PASS — database remained after uninstall |
| Upgrade preserving user data | PASS — repeated install preserved the isolated database and its SHA256 |
| Fresh install on clean Windows machine | NOT TESTED — this host has development tooling |
| Upgrade with existing financial data | NOT TESTED |
| Clean-machine runtime dependency validation | NOT TESTED — development host used for acceptance smoke tests |

Testing was performed on the current Windows 11 x64 development host. The installer is not claimed to be commercially ready until clean Windows 10/11 x64 and upgrade tests are executed.
