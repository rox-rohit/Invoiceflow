from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout

from src.ledger import LedgerStore
from .branding import logo_pixmap


class OnboardingDialog(QDialog):
    def __init__(self, database: str | Path, parent=None):
        super().__init__(parent)
        self.database=database
        self.setWindowTitle("Welcome to InvoiceFlow")
        self.setModal(False)
        layout=QVBoxLayout(self)
        logo=QLabel(); logo.setPixmap(logo_pixmap(120)); layout.addWidget(logo)
        layout.addWidget(QLabel("Set up your business profile. Optional fields can be completed later in Settings."))
        form=QFormLayout(); self.fields={}
        for key,label in (("owner_name","Owner name"),("name","Business/shop name"),("business_type","Business type"),("address","Address"),("phone","Phone"),("email","Email"),("base_currency","Currency"),("financial_year_start","Financial year start month"),("date_format","Date format")):
            field=QComboBox() if key=="business_type" else QLineEdit()
            if key=="business_type": field.addItems(["Retail shop","Restaurant/cafe","Wholesale/distribution","Service business","Other"])
            if key=="base_currency": field.setText("INR")
            if key=="financial_year_start": field.setText("4")
            if key=="date_format": field.setText("dd/MM/yyyy")
            self.fields[key]=field; form.addRow(label,field)
        layout.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self._save); buttons.rejected.connect(self._skip); layout.addWidget(buttons)

    def _save(self):
        name=self.fields["name"].currentText() if isinstance(self.fields["name"],QComboBox) else self.fields["name"].text().strip()
        if not name:
            self.fields["name"].setFocus(); return
        values={key:(field.currentText() if isinstance(field,QComboBox) else field.text().strip()) for key,field in self.fields.items()}
        ledger=LedgerStore(self.database)
        try:
            ledger.update_business_profile(**{key:value for key,value in values.items() if key!="date_format"})
            ledger.set_setting("date_format",values["date_format"]); ledger.set_setting("onboarding_complete","1")
        finally: ledger.close()
        self.accept()

    def _skip(self):
        ledger=LedgerStore(self.database)
        try: ledger.set_setting("onboarding_complete","1")
        finally: ledger.close()
        self.reject()
