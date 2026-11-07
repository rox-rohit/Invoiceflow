"""Run privacy-safe synthetic batch stability checks at progressive sizes.

These results measure throughput and failure isolation only. They are not
invoice-extraction accuracy benchmarks.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.batch import process_batch
from tools.generate_stress_corpus import make_pdf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--maximum", type=int, default=500)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    for index in range(args.maximum):
        path = args.destination / f"invoice_{index:05d}.pdf"
        if not path.exists():
            make_pdf(path, index)
    paths = sorted(args.destination.glob("*.pdf"))
    results = []
    for size in (1, 10, 25, 50, 100, 250, 500):
        if size > len(paths):
            continue
        started = time.perf_counter()
        processed = process_batch(paths[:size], max_files=max(2000, size), workers=2)
        elapsed = time.perf_counter() - started
        results.append({"batch_size": size, "results": len(processed), "errors": sum(item.status.value == "ERROR" for item in processed), "seconds": round(elapsed, 3), "throughput": round(len(processed) / elapsed, 2) if elapsed else None})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
