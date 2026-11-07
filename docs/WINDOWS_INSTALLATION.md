# InvoiceFlow Windows installation

## Install

Download `InvoiceFlow_Setup_2.5.1.exe` and verify its SHA256 checksum before running it. The installer targets 64-bit Windows 10/11 and includes the complete PyInstaller onedir application, Python runtime, Qt plugins, DLLs and approved IF branding. No Python, pip or development tools are required.

The default installation directory is:

`C:\Program Files\InvoiceFlow`

The installer creates a Start Menu shortcut and offers an optional desktop shortcut. It can launch InvoiceFlow after installation.

## User data and upgrades

Financial history, settings, imports, backups and onboarding state are stored outside the installation directory:

`%LOCALAPPDATA%\InvoiceFlow\history.db`

Installing a newer version replaces application files only. It does not overwrite or reset this database. Close InvoiceFlow before upgrading so the installer can replace locked files safely.

## Uninstall

Uninstall InvoiceFlow from Windows Settings or Apps and Features. The uninstaller removes installed application files and shortcuts but preserves `%LOCALAPPDATA%\InvoiceFlow` by default. Keep a verified backup before uninstalling.

## Recovery

Use the application's backup and restore tools for database recovery. If Windows SmartScreen warns about the installer, the release may be unsigned; verify the checksum and download source before continuing. This project does not claim that the installer is digitally signed.

## Known prerequisites

The package is self-contained and does not require Python, pip, PySide6, PyMuPDF or a separately installed SQLite. Windows system components and standard Microsoft runtime components may still be required by the bundled Qt/Python binaries; clean-machine validation is required before commercial distribution.
