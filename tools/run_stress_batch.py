from __future__ import annotations
import argparse, time
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.batch import process_batch

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("folder",type=Path); args=parser.parse_args(); files=sorted(args.folder.glob("*.pdf")); start=time.perf_counter(); results=process_batch(files,max_files=max(2000,len(files)),workers=2); elapsed=time.perf_counter()-start; print({"files":len(files),"results":len(results),"errors":sum(r.status.value=="ERROR" for r in results),"elapsed_seconds":round(elapsed,3),"throughput":round(len(results)/elapsed,2)})

if __name__ == "__main__": main()
