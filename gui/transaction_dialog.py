from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QVBoxLayout

from src.ledger import LedgerTransaction, TRANSACTION_TYPES


class TransactionDialog(QDialog):
    def __init__(self, default_type: str = "sale", parent=None):
        super().__init__(parent); self.setWindowTitle("Add transaction"); self.resize(460, 420)
        layout=QVBoxLayout(self); form=QFormLayout(); self.fields={}
        self.type=QComboBox(); allowed=["sale","purchase","expense","collection","supplier_payment","sales_return","purchase_return","adjustment"]
        for kind in allowed: self.type.addItem(kind.replace("_"," ").title(),kind)
        if default_type in allowed: self.type.setCurrentIndex(allowed.index(default_type))
        self.date=QDateEdit(QDate.currentDate()); self.date.setCalendarPopup(True); self.date.setDisplayFormat("dd MMM yyyy")
        for name, widget, label in (("transaction_type",self.type,"Transaction type"),("transaction_date",self.date,"Date")):
            self.fields[name]=widget; form.addRow(label+":",widget)
        for name,label,placeholder in (("amount","Amount","Required"),("currency","Currency","INR"),("counterparty","Customer / supplier","Optional"),("category","Category","e.g. Rent"),("reference_number","Reference","Optional"),("payment_method","Payment method","Optional"),("description","Description","What was this for?")):
            edit=QLineEdit(); edit.setPlaceholderText(placeholder); self.fields[name]=edit; form.addRow(label+":",edit)
        self.status=QComboBox();
        for value in ("unknown","unpaid","partially_paid","paid","not_applicable"): self.status.addItem(value.replace("_"," ").title(),value)
        form.addRow("Payment status:",self.status); layout.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def transaction(self) -> LedgerTransaction:
        amount=self.fields["amount"].text().strip()
        if not amount: raise ValueError("Amount is required")
        return LedgerTransaction(transaction_type=self.type.currentData(),transaction_date=self.date.date().toPython().isoformat(),amount=amount,currency=self.fields["currency"].text().strip() or "INR",counterparty=self.fields["counterparty"].text().strip(),category=self.fields["category"].text().strip(),reference_number=self.fields["reference_number"].text().strip(),payment_method=self.fields["payment_method"].text().strip(),description=self.fields["description"].text().strip(),payment_status=self.status.currentData(),verification_status="VERIFIED")

    def accept(self):
        try: self._transaction=self.transaction()
        except Exception as exc: QMessageBox.warning(self,"Transaction not saved",str(exc)); return
        super().accept()
