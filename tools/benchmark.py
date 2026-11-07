"""Run a transparent local benchmark over a recovered invoice corpus."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.batch import process_batch

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--ground-truth", type=Path)
    args = parser.parse_args()
    files = sorted(args.folder.rglob("*.pdf"), key=lambda p: p.as_posix().lower())
    if args.limit:
        files = files[:args.limit]
    results = process_batch(files, max_files=max(500, args.limit or 500))
    counts = {}
    for result in results:
        counts[result.status.value] = counts.get(result.status.value, 0) + 1
    report={"input_files":len(files),"results":len(results),"status_counts":counts}
    if args.ground_truth:
        truth={row["file"]:row for row in json.loads(args.ground_truth.read_text(encoding="utf-8"))}; metrics={}
        for field in ("invoice_number","invoice_date","vendor_name","customer_name","subtotal","tax_amount","total_amount"):
            correct=missing=ambiguous=0; applicable=0
            for record in results:
                row=truth.get(Path(record.source_file).name)
                if not row or field not in row: continue
                applicable+=1; actual=getattr(record,field); expected=row[field]
                if actual in (None,""): missing+=1
                elif isinstance(expected,(int,float)):
                    correct += abs(float(actual)-float(expected)) <= 0.02
                else:
                    correct += str(actual).strip().casefold()==str(expected).strip().casefold()
            metrics[field]={"applicable":applicable,"correct":correct,"missing":missing,"ambiguous":ambiguous,"accuracy":(correct/applicable if applicable else None)}
        report["field_metrics"]=metrics
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
