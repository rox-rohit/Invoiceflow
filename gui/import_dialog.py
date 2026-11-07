from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from src.importer import ALIASES, ImportService
from src.ledger import LedgerStore


class ImportDialog(QDialog):
    """Preview, map, validate, then explicitly confirm a ledger import."""
    def __init__(self, store: LedgerStore, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import financial data")
        self.resize(920, 650)
        self.store = store
        self.service = ImportService(store)
        self.preview_data = None
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.kind = QComboBox()
        for label, key in (("Sales", "sales"), ("Sales returns", "sales_returns"), ("Purchases", "purchases"), ("Purchase returns", "purchase_returns"), ("Operating expenses", "expenses"), ("Customer collections", "collections"), ("Supplier payments", "supplier_payments")):
            self.kind.addItem(label, key)
        self.kind.currentIndexChanged.connect(self._kind_changed)
        form.addRow("Import type", self.kind)
        file_row = QHBoxLayout(); self.file_label = QLabel("No file selected")
        choose = QPushButton("Choose CSV / Excel")
        choose.clicked.connect(self._choose)
        template = QPushButton("Save import template")
        template.clicked.connect(self._template)
        file_row.addWidget(self.file_label, 1); file_row.addWidget(choose); file_row.addWidget(template)
        form.addRow("File", file_row)
        root.addLayout(form)
        root.addWidget(QLabel("Confirm the column mapping before importing. Invalid rows are shown with their reasons."))
        self.mapping_table = QTableWidget(0, 2); self.mapping_table.setHorizontalHeaderLabels(["InvoiceFlow field", "Source column"]); root.addWidget(self.mapping_table, 1)
        self.rows_table = QTableWidget(0, 4); self.rows_table.setHorizontalHeaderLabels(["Row", "Date", "Amount", "Validation / duplicate review"]); root.addWidget(self.rows_table, 2)
        self.summary = QLabel("Select a file to preview."); root.addWidget(self.summary)
        self.include_duplicates = QCheckBox("Import rows flagged as possible duplicates (review first)")
        root.addWidget(self.include_duplicates)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.import_button = buttons.addButton("Import valid rows", QDialogButtonBox.AcceptRole)
        self.import_button.setEnabled(False)
        buttons.rejected.connect(self.reject); self.import_button.clicked.connect(self._confirm)
        root.addWidget(buttons)

    def _choose(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose financial data", str(Path.home()), "Data files (*.csv *.xlsx *.xlsm)")
        if not path: return
        self.path = Path(path); self.file_label.setText(self.path.name)
        try: self._make_preview()
        except Exception as exc: QMessageBox.warning(self, "Cannot preview import", str(exc))

    def _kind_changed(self, *_):
        if getattr(self, "preview_data", None):
            try: self._make_preview()
            except Exception as exc: QMessageBox.warning(self, "Cannot preview import", str(exc))

    def _make_preview(self):
        self.preview_data = self.service.preview(self.path, self.kind.currentData())
        preview = self.preview_data
        self.mapping_table.setRowCount(len(ALIASES)); self.mapping_widgets = {}
        for row, field in enumerate(ALIASES):
            self.mapping_table.setItem(row, 0, QTableWidgetItem(field.replace("_", " ").title()))
            combo = QComboBox(); combo.addItem("— Not mapped —", "")
            for column in preview.columns: combo.addItem(column, column)
            if preview.mapping.get(field):
                index = combo.findData(preview.mapping[field]); combo.setCurrentIndex(max(0, index))
            self.mapping_table.setCellWidget(row, 1, combo); self.mapping_widgets[field] = combo
        for combo in self.mapping_widgets.values(): combo.currentIndexChanged.connect(self._mapping_changed)
        self._render_preview()

    def _mapping_changed(self, *_):
        if not self.preview_data: return
        mapping = {field: combo.currentData() or "" for field, combo in self.mapping_widgets.items()}
        try:
            self.preview_data = self.service.preview(self.path, self.kind.currentData(), mapping)
            self._render_preview()
        except Exception as exc: QMessageBox.warning(self, "Mapping error", str(exc))

    def _render_preview(self):
        preview = self.preview_data
        self.rows_table.setRowCount(min(len(preview.rows), 500))
        for row_number, item in enumerate(preview.rows[:500]):
            status = "; ".join(item.errors) if item.errors else (f"Possible duplicate of row/transaction {item.duplicate_of}" if item.duplicate_of else "Valid")
            values = (item.row_number, item.values.get("transaction_date", ""), item.values.get("amount", ""), status)
            for column, value in enumerate(values): self.rows_table.setItem(row_number, column, QTableWidgetItem(str(value)))
        self.summary.setText(f"Rows: {len(preview.rows):,}   Valid: {preview.valid_count:,}   Invalid: {preview.invalid_count:,}   Possible duplicates: {preview.duplicate_count:,}" + ("   This exact file was already imported." if preview.already_imported else ""))
        self.import_button.setEnabled(preview.valid_count > 0 and not preview.already_imported)

    def _confirm(self):
        if not self.preview_data: return
        answer = QMessageBox.question(self, "Confirm import", f"Import {self.preview_data.valid_count} valid row(s)? Invalid rows will remain excluded. Possible duplicates are excluded unless you opt in.")
        if answer != QMessageBox.Yes: return
        try:
            result = self.service.confirm(self.preview_data, self.include_duplicates.isChecked())
            QMessageBox.information(self, "Import complete", f"Imported: {result['imported']}\nInvalid: {result['invalid']}\nPossible duplicates: {result['duplicates']}\nImport batch: {result['batch_id'] or 'Previously imported'}")
            self.accept()
        except Exception as exc: QMessageBox.critical(self, "Import failed", str(exc))

    def _template(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save import template", str(Path.home() / f"invoiceflow_{self.kind.currentData()}_template.csv"), "CSV (*.csv);;Excel (*.xlsx)")
        if not path: return
        try:
            self.service.write_template(path, self.kind.currentData(), path.casefold().endswith(".xlsx"))
            QMessageBox.information(self, "Template saved", f"Saved template to {path}")
        except Exception as exc: QMessageBox.critical(self, "Template failed", str(exc))
