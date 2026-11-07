from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class DocumentClassification:
    category: str
    score: float
    evidence: tuple[str, ...]
    is_invoice: bool

def classify_text(text: str, scanned: bool=False) -> DocumentClassification:
    if scanned: return DocumentClassification("scanned",1.0,("insufficient native text",),False)
    rules={
        "invoice":(r"\binvoice\b",r"\bgrand\s+total\b",r"\bsubtotal\b",r"\binvoice\s+(?:no|number)\b"),
        "credit_note":(r"\bcredit\s+note\b",r"\bcredit\b"),
        "debit_note":(r"\bdebit\s+note\b",r"\bdebit\b"),
        "receipt":(r"\breceipt\b",r"\bamount\s+paid\b"),
        "purchase_order":(r"\bpurchase\s+order\b",r"\bpo\s*(?:no|number)\b"),
        "statement":(r"\baccount\s+statement\b",r"\bstatement\s+period\b"),
    }
    scores=[]
    for category,patterns in rules.items():
        evidence=tuple(pattern for pattern in patterns if re.search(pattern,text,re.I)); scores.append((len(evidence)/len(patterns),category,evidence))
    score,category,evidence=max(scores)
    is_invoice=category in {"invoice","credit_note","debit_note"} and score>=0.5
    return DocumentClassification(category,score,evidence,is_invoice)
