from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class JobState:
    job_id: str
    total: int = 0
    completed: int = 0
    completed_sources: list[str] | None = None
    cancelled: bool = False
    failed: int = 0
    def __post_init__(self):
        if self.completed_sources is None: self.completed_sources=[]

class JobStore:
    def __init__(self, directory: str | Path): self.directory=Path(directory); self.directory.mkdir(parents=True,exist_ok=True)
    def path(self,job_id: str) -> Path: return self.directory/f"{job_id}.json"
    def save(self,state: JobState) -> None: self.path(state.job_id).write_text(json.dumps(asdict(state),indent=2),encoding="utf-8")
    def load(self,job_id: str) -> JobState | None:
        path=self.path(job_id)
        if not path.exists(): return None
        return JobState(**json.loads(path.read_text(encoding="utf-8")))
    def clear(self,job_id: str) -> None: self.path(job_id).unlink(missing_ok=True)
