from __future__ import annotations
import json
from pathlib import Path
from .models import InvoiceRecord

def correction_examples(records: list[InvoiceRecord]) -> list[dict]:
    examples=[]
    for record in records:
        for correction in record.corrections:
            examples.append({"record_id":record.record_id,"source_file":record.source_file,"field_name":correction.field_name,"original_value":correction.original_value,"corrected_value":correction.corrected_value,"timestamp":correction.timestamp,"extraction_version":record.extraction_version,"user_verified":True})
    return examples

def export_correction_feedback(records: list[InvoiceRecord], destination: str | Path) -> Path:
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True); destination.write_text(json.dumps(correction_examples(records),indent=2,ensure_ascii=False),encoding="utf-8"); return destination
