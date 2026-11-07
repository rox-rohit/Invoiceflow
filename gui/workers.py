import threading
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from src.batch import process_batch
from src.config import DATA_DIR

class BatchWorker(QObject):
    progress=Signal(int,int,str); result=Signal(object); finished=Signal(object); failed=Signal(str)
    def __init__(self, paths): super().__init__(); self.paths=paths; self.cancel_event=threading.Event()
    @Slot()
    def run(self):
        try: self.finished.emit(process_batch(self.paths, self._progress, cancel_event=self.cancel_event, result_callback=self.result.emit, state_path=DATA_DIR/"jobs"/"batch.json", job_id="current", resume=False))
        except Exception as exc: self.failed.emit(str(exc))
    def _progress(self,current,total,name):
        self.progress.emit(current,total,name)
    def cancel(self): self.cancel_event.set()
