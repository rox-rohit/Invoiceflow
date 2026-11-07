from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import QApplication,QFileDialog,QFrame,QHBoxLayout,QLabel,QLineEdit,QMainWindow,QMessageBox,QPushButton,QProgressBar,QStackedWidget,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from src.config import APP_NAME, DB_PATH
from src.exporter import export_csv, export_excel, export_json
from src.models import InvoiceRecord, ProcessingStatus
from src.storage import HistoryStore
from src.anomaly import detect_anomalies
from src.duplicate import detect_duplicates
from src.financials import transactions_from_invoices
from src.reports import build_report, period_for
from src.ledger import LedgerStore
from .styles import STYLE
from .workers import BatchWorker
from .widgets import InvoiceEditDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(f"{APP_NAME} — PDF invoices → structured data"); self.setMinimumSize(1050,680); self.records=[]; self.store=HistoryStore(DB_PATH); self._build(); self._refresh()
    def _build(self):
        self.setStyleSheet(STYLE); root=QWidget(); layout=QHBoxLayout(root); layout.setContentsMargins(0,0,0,0)
        side=QFrame(objectName="sidebar"); side.setFixedWidth(220); sl=QVBoxLayout(side); sl.setContentsMargins(12,22,12,12)
        brand=QLabel("InvoiceFlow",objectName="brand"); tag=QLabel("PDF invoices →\nstructured data",objectName="tagline"); sl.addWidget(brand); sl.addWidget(tag); sl.addSpacing(26)
        self.nav=[]
        for label in ["Dashboard","Process Invoices","Results","Review","Reports","Settings","About"]:
            b=QPushButton(label,objectName="nav"); b.setCheckable(True); b.clicked.connect(lambda checked, x=label:self._navigate(x)); sl.addWidget(b); self.nav.append(b)
        sl.addStretch(); sl.addWidget(QLabel("InvoiceFlow · Built by Rohit Ahirwar",objectName="tagline")); layout.addWidget(side)
        self.stack=QStackedWidget(); layout.addWidget(self.stack,1); self.setCentralWidget(root)
        self.dashboard=self._dashboard(); self.process=self._process(); self.results=self._results(); self.review=self._review(); self.reports=self._reports(); self.settings=self._simple("Settings","Application data is stored in your Windows local application data folder.\n\nNo invoice contents leave this computer."); self.about=self._simple("About","InvoiceFlow\nPDF invoices → structured data\n\nDeterministic local invoice processing with transparent review flags.")
        for w in [self.dashboard,self.process,self.results,self.review,self.reports,self.settings,self.about]: self.stack.addWidget(w)
        self._navigate("Dashboard")
    def _page(self,title):
        w=QWidget(); v=QVBoxLayout(w); v.setContentsMargins(28,24,28,24); h=QLabel(title); h.setStyleSheet("font-size:22pt;font-weight:700;"); v.addWidget(h); return w,v
    def _simple(self,title,text):
        w,v=self._page(title); l=QLabel(text); l.setStyleSheet("font-size:12pt;"); v.addWidget(l); v.addStretch(); return w
    def _dashboard(self):
        w,v=self._page("Dashboard"); self.stats=QLabel(); self.stats.setStyleSheet("font-size:14pt;background:white;border:1px solid #e1e7ea;border-radius:8px;padding:20px;"); v.addWidget(self.stats); v.addStretch(); return w
    def _process(self):
        w,v=self._page("Process Invoices"); self.selected=QLabel("Drop PDF or ZIP files here, or choose files below."); v.addWidget(self.selected); row=QHBoxLayout(); choose=QPushButton("Choose files"); choose.clicked.connect(self._choose); clear=QPushButton("Clear"); clear.clicked.connect(lambda:self._set_files([])); row.addWidget(choose); row.addWidget(clear); row.addStretch(); v.addLayout(row); self.progress=QProgressBar(); self.current=QLabel(); v.addWidget(self.progress); v.addWidget(self.current); self.start=QPushButton("Start Processing",objectName="primary"); self.start.clicked.connect(self._start); self.cancel=QPushButton("Cancel"); self.cancel.setEnabled(False); self.cancel.clicked.connect(self._cancel); v.addWidget(self.start); v.addWidget(self.cancel); v.addStretch(); self.files=[]; return w
    def _results(self):
        w,v=self._page("Results"); row=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("Search invoice number, vendor or filename"); self.search.textChanged.connect(self._refresh_table); row.addWidget(self.search)
        for label, kind in (("Export Excel", "xlsx"), ("Export CSV", "csv"), ("Export JSON", "json")):
            export=QPushButton(label); export.clicked.connect(lambda checked=False, k=kind:self._export(k)); row.addWidget(export)
        v.addLayout(row); self.table=QTableWidget(0,8); self.table.setHorizontalHeaderLabels(["Invoice Number","Vendor","Date","Subtotal","Tax","Total","Status","Source File"]); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.cellDoubleClicked.connect(self._detail); v.addWidget(self.table); return w
    def _review(self):
        w,v=self._page("Review"); self.review_text=QLabel("No records require review."); self.review_text.setWordWrap(True); v.addWidget(self.review_text); v.addStretch(); return w
    def _reports(self):
        w,v=self._page("Reports & Business Insights"); self.report_period=QLineEdit("month"); self.report_period.setPlaceholderText("month, last_6_months, last_12_months, year_to_date"); v.addWidget(self.report_period); generate=QPushButton("Generate report"); generate.clicked.connect(self._generate_report); v.addWidget(generate); self.report_output=QLabel("Reports use explicitly classified financial transactions. Invoice documents alone are not treated as cash received or paid."); self.report_output.setWordWrap(True); v.addWidget(self.report_output); v.addStretch(); return w
    def _navigate(self,label):
        index={"Dashboard":0,"Process Invoices":1,"Results":2,"Review":3,"Reports":4,"Settings":5,"About":6}[label]; self.stack.setCurrentIndex(index); [b.setChecked(b.text()==label) for b in self.nav]; self._refresh()
    def _generate_report(self):
        try:
            period=period_for(self.report_period.text().strip() or "month"); ledger=LedgerStore(DB_PATH); transactions=ledger.list(verified_only=True); ledger.close()
            if not transactions:
                records=self.store.load(); explicit={r.record_id:r.invoice_type for r in records if r.invoice_type in {"sale","purchase","expense","collection","payment"}}; transactions=transactions_from_invoices(records,explicit)
            report=build_report(transactions,period,"INR"); metrics="\n".join(f"{metric.name}: {metric.value:.2f} {metric.currency}" for metric in report.metrics.values() if metric.value is not None); notes="\n".join(report.data_quality) or "Data quality checks passed for available records."; self.report_output.setText(metrics+"\n\n"+notes)
        except Exception as exc: self.report_output.setText(f"Unable to generate report: {exc}")
    def _choose(self):
        files,_=QFileDialog.getOpenFileNames(self,"Select invoice PDFs or ZIP files",str(Path.home()),"Invoices (*.pdf *.zip)"); self._set_files(files)
    def _set_files(self,files): self.files=files; self.selected.setText(f"{len(files)} input file(s) selected"); self.start.setEnabled(bool(files))
    def _start(self):
        self.start.setEnabled(False); self.cancel.setEnabled(True); self.progress.setValue(0); self.thread=QThread(); self.worker=BatchWorker(self.files); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.progress.connect(lambda c,t,n:(self.progress.setMaximum(t),self.progress.setValue(c),self.current.setText(f"{c}/{t}: {n}"))); self.worker.result.connect(self._save_incremental); self.worker.finished.connect(self._finished); self.worker.failed.connect(lambda e: QMessageBox.critical(self,"Processing error",e)); self.worker.finished.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit); self.thread.start()
    def _cancel(self):
        if hasattr(self,"worker"): self.worker.cancel(); self.current.setText("Cancellation requested; finishing active documents...")
    def _save_incremental(self,record): self.store.save([record])
    def _finished(self,records):
        history=self.store.load(); records=detect_duplicates(records,history); self.records=[detect_anomalies(record,history) for record in records]; self.store.save(self.records); self.start.setEnabled(True); self.cancel.setEnabled(False); self._refresh(); self._navigate("Results")
    def _refresh(self):
        try: self.records=self.store.load()
        except Exception: pass
        if hasattr(self,"stats"):
            counts={s:sum(r.status==s for r in self.records) for s in ProcessingStatus}; self.stats.setText(f"Total invoices processed: {len(self.records)}\n\nFound: {counts[ProcessingStatus.FOUND]}    Needs review: {counts[ProcessingStatus.NEEDS_REVIEW]}    Requires OCR: {counts[ProcessingStatus.REQUIRES_OCR]}    Errors: {counts[ProcessingStatus.ERROR]}")
        if hasattr(self,"table"): self._refresh_table()
        if hasattr(self,"review_text"): self.review_text.setText("\n".join(f"{r.invoice_number or '(missing number)'} — {i.message}" for r in self.records if r.status==ProcessingStatus.NEEDS_REVIEW for i in r.issues) or "No records require review.")
    def _refresh_table(self):
        term=self.search.text().lower() if hasattr(self,"search") else ""; rows=[r for r in self.records if not term or term in (r.invoice_number+r.vendor_name+r.source_file).lower()]; self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            values=[r.invoice_number,r.vendor_name,r.invoice_date,"" if r.subtotal is None else f"{r.subtotal:.2f}","" if r.tax_amount is None else f"{r.tax_amount:.2f}","" if r.total_amount is None else f"{r.total_amount:.2f}",r.status.value,Path(r.source_file).name]
            for j,x in enumerate(values): self.table.setItem(i,j,QTableWidgetItem(str(x)))
        self.table.resizeColumnsToContents()
    def _detail(self,row,_col):
        r=[x for x in self.records if x.invoice_number==self.table.item(row,0).text() and Path(x.source_file).name==self.table.item(row,7).text()];
        if r:
            dialog=InvoiceEditDialog(r[0], self)
            if dialog.exec():
                self.store.update(r[0])
                if dialog.transaction_type:
                    ledger=LedgerStore(DB_PATH)
                    existing=[item for item in ledger.list() if item.source_record_id==r[0].record_id and item.transaction_type==dialog.transaction_type]
                    if not existing:
                        proposal=ledger.propose_from_invoice(r[0],dialog.transaction_type); proposal.verification_status="VERIFIED"; ledger.add(proposal)
                    ledger.close()
                self._refresh()
    def _export(self,kind):
        path,_=QFileDialog.getSaveFileName(self,"Export results",str(Path.home()/f"invoiceflow_export.{kind}"),f"{kind.upper()} (*.{kind})");
        if not path:return
        try:
            selected=[]
            for index in self.table.selectionModel().selectedRows() if hasattr(self,"table") else []:
                number=self.table.item(index.row(),0).text(); source=self.table.item(index.row(),7).text()
                selected.extend(r for r in self.records if r.invoice_number==number and Path(r.source_file).name==source)
            records=selected or self.records
            (export_excel if kind=="xlsx" else export_csv if kind=="csv" else export_json)(records,path); QMessageBox.information(self,"Export complete",f"Saved {len(records)} invoice(s) to {path}")
        except Exception as exc: QMessageBox.critical(self,"Export failed",str(exc))
