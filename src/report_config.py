from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

@dataclass
class SavedReportConfig:
    name: str
    period_kind: str = "month"
    currency: str = ""
    categories: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    suppliers: list[str] = field(default_factory=list)
    payment_status: str = ""

class ReportConfigStore:
    def __init__(self,path: str | Path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    def load(self) -> list[SavedReportConfig]:
        if not self.path.exists(): return []
        return [SavedReportConfig(**item) for item in json.loads(self.path.read_text(encoding="utf-8"))]
    def save(self,config: SavedReportConfig) -> None:
        configs=[item for item in self.load() if item.name!=config.name]; configs.append(config); self.path.write_text(json.dumps([asdict(item) for item in configs],indent=2),encoding="utf-8")
