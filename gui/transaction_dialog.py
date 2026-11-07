from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QVBoxLayout

from src.ledger import LedgerTransaction, TRANSACTION_TYPES


class TransactionDialog(QDialog):
    def __init__(self, default_type: str = "sale", parent=None, transaction: LedgerTransaction | None = None):
        super().__init__(parent); self.transaction_to_edit=transaction; self.setWindowTitle("Edit transaction" if transaction else "Add transaction"); self.resize(460, 420)
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
        self.status.setCurrentIndex(self.status.findData("unknown")); self.status.setEnabled(False)
        form.addRow("Allocation status:",self.status); layout.addLayout(form)
        note=QLineEdit("Invoice balances are calculated from explicit payment allocations."); note.setReadOnly(True); form.addRow("Note:",note)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        if transaction:
            self.type.setCurrentIndex(max(0,self.type.findData(transaction.transaction_type)))
            self.date.setDate(QDate.fromString(transaction.transaction_date,"yyyy-MM-dd"))
            for name in ("amount","currency","counterparty","category","reference_number","payment_method","description"):
                value=getattr(transaction,name,"")
                if name=="amount" and value is not None: value=str(value)
                self.fields[name].setText(str(value or ""))

    def transaction(self) -> LedgerTransaction:
        amount=self.fields["amount"].text().strip()
        if not amount: raise ValueError("Amount is required")
        original=self.transaction_to_edit
        return LedgerTransaction(transaction_id=original.transaction_id if original else None,business_id=original.business_id if original else 1,transaction_type=self.type.currentData(),transaction_date=self.date.date().toPython().isoformat(),document_date=original.document_date if original else "",due_date=original.due_date if original else "",amount=amount,currency=self.fields["currency"].text().strip() or "INR",counterparty=self.fields["counterparty"].text().strip(),category=self.fields["category"].text().strip(),reference_number=self.fields["reference_number"].text().strip(),payment_method=self.fields["payment_method"].text().strip(),description=self.fields["description"].text().strip(),payment_status="unknown",source_record_id=original.source_record_id if original else None,source_file=original.source_file if original else "",verification_status="USER_REVIEWED",metadata=original.metadata.copy() if original else {})

    def accept(self):
        try: self._transaction=self.transaction()
        except Exception as exc: QMessageBox.warning(self,"Transaction not saved",str(exc)); return
        super().accept()
