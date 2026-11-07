from __future__ import annotations
from datetime import datetime, timezone
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout
from src.models import Correction, InvoiceRecord, LineItem
from src.validator import validate

EDITABLE_FIELDS=("invoice_number","invoice_date","due_date","vendor_name","customer_name","currency","subtotal","discount","tax_rate","tax_amount","total_amount","payment_terms","purchase_order_number")

class InvoiceEditDialog(QDialog):
    def __init__(self, record: InvoiceRecord, parent=None):
        super().__init__(parent); self.setWindowTitle("Review and correct invoice"); self.resize(760,560); self.record=record; self.fields={}; self.transaction_type=None
        layout=QVBoxLayout(self); form=QFormLayout()
        if record.manually_corrected:
            original_text="; ".join(f"{name}: {record.original_data.get(name, '')} -> {getattr(record,name)}" for name in sorted(record.manually_corrected))
            notice=QLabel("Manual corrections preserved: " + original_text); notice.setWordWrap(True); layout.addWidget(notice)
        for name in EDITABLE_FIELDS:
            edit=QLineEdit("" if getattr(record,name) is None else str(getattr(record,name))); self.fields[name]=edit; form.addRow(name.replace("_"," ").title()+":",edit)
        layout.addLayout(form)
        self.items=QTableWidget(len(record.line_items),7); self.items.setHorizontalHeaderLabels(["Description","Qty","Unit","Unit price","Tax %","Tax amount","Total"])
        for row,item in enumerate(record.line_items):
            for col,value in enumerate((item.description,item.quantity,item.unit,item.unit_price,item.tax_rate,item.tax_amount,item.total)):
                self.items.setItem(row,col,QTableWidgetItem("" if value is None else str(value)))
        layout.addWidget(self.items)
        buttons=QHBoxLayout(); add=QPushButton("Add line item"); remove=QPushButton("Remove selected"); add.clicked.connect(self._add); remove.clicked.connect(self._remove); buttons.addWidget(add); buttons.addWidget(remove); buttons.addStretch(); layout.addLayout(buttons)
        approval=QHBoxLayout(); approval.addWidget(QLabel("Save as verified financial transaction:"))
        for label,kind in (("Sale","sale"),("Purchase","purchase"),("Expense","expense"),("Sales return","sales_return"),("Purchase return","purchase_return")):
            button=QPushButton(label); button.clicked.connect(lambda checked=False, value=kind:self._approve(value)); approval.addWidget(button)
        approval.addStretch(); layout.addLayout(approval)
        box=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); box.accepted.connect(self._accept); box.rejected.connect(self.reject); layout.addWidget(box)

    def _add(self): self.items.insertRow(self.items.rowCount())
    def _remove(self):
        rows=sorted({index.row() for index in self.items.selectedIndexes()}, reverse=True)
        for row in rows: self.items.removeRow(row)

    @staticmethod
    def _value(text: str, old):
        if old is None or isinstance(old,(int,float)):
            if not text.strip(): return None
            try: return float(text.replace(",",""))
            except ValueError: return text
        return text.strip()

    def _approve(self, transaction_type):
        self.transaction_type=transaction_type; self._accept()

    def _accept(self):
        original=self.record.original_data or self.record.to_dict()
        for name,edit in self.fields.items():
            old=getattr(self.record,name); new=self._value(edit.text(),old)
            if new != old:
                if not self.record.original_data: self.record.original_data=dict(original)
                self.record.corrections.append(Correction(name,old,new,datetime.now(timezone.utc).isoformat()))
                self.record.manually_corrected.add(name); setattr(self.record,name,new)
        items=[]
        for row in range(self.items.rowCount()):
            def cell(col): return self.items.item(row,col).text().strip() if self.items.item(row,col) else ""
            description=cell(0)
            if not description: continue
            def num(col):
                value=cell(col)
                try: return float(value.replace(",","")) if value else None
                except ValueError: return None
            items.append(LineItem(description=description,quantity=num(1),unit=cell(2),unit_price=num(3),tax_rate=num(4),tax_amount=num(5),total=num(6),source_row=row))
        self.record.line_items=items; validate(self.record,is_invoice=True); self.accept()
