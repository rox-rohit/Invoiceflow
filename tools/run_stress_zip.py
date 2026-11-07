from __future__ import annotations
import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.batch import process_batch

if __name__=="__main__":
    path=Path(sys.argv[1]); start=time.perf_counter(); results=process_batch([path],max_files=2000,workers=2); elapsed=time.perf_counter()-start; print({"files":len(results),"errors":sum(r.status.value=="ERROR" for r in results),"elapsed_seconds":round(elapsed,3),"throughput":round(len(results)/elapsed,2)})
