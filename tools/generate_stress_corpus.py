"""Generate synthetic PDFs for throughput and failure-isolation testing only."""
from __future__ import annotations
import argparse, zipfile
from pathlib import Path
import pymupdf

def make_pdf(path: Path, index: int) -> None:
    doc=pymupdf.open(); page=doc.new_page(); page.insert_text((36,36),f"TAX INVOICE\nSeller: Stress Vendor {index % 20}\nInvoice Number: ST-{index:06d}\nInvoice Date: 2026-01-{(index % 28)+1:02d}\nBill To: Stress Customer\nDescription Qty Rate Amount\nService {index % 5} 1 10.00 10.00\nSubtotal: 10.00\nTax: 1.80\nGrand Total: 11.80"); doc.save(path); doc.close()

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("destination",type=Path); parser.add_argument("--count",type=int,default=2000); parser.add_argument("--zip",action="store_true"); args=parser.parse_args(); args.destination.mkdir(parents=True,exist_ok=True)
    for i in range(args.count): make_pdf(args.destination/f"invoice_{i:05d}.pdf",i)
    if args.zip:
        with zipfile.ZipFile(args.destination.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(args.destination.glob('*.pdf')): archive.write(path,path.name)
    print(f"Generated {args.count} synthetic PDFs at {args.destination}; these are stress fixtures, not accuracy evidence.")

if __name__ == "__main__": main()
