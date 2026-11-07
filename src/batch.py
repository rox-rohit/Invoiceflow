from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import threading
import zipfile
from concurrent.futures import Future, ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Iterator

from .duplicate import detect_duplicates
from .invoice_parser import parse_invoice
from .models import InvoiceRecord, ProcessingStatus, ValidationIssue
from .pdf_extractor import extract_pdf
from .job import JobState, JobStore

DEFAULT_MAX_FILES = 2000
DEFAULT_MAX_BYTES = 100 * 1024 * 1024

@dataclass(frozen=True)
class SourceSpec:
    kind: str
    path: Path
    member: str = ""
    display_name: str = ""

@dataclass
class Discovery:
    sources: list[SourceSpec]
    temporary_archives: list[Path]
    total_uncompressed_bytes: int = 0

def _safe_member_name(name: str) -> None:
    normalized=name.replace("\\", "/")
    pure=PurePosixPath(normalized)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"Unsafe ZIP path: {name}")

def _copy_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo, destination: Path, max_bytes: int) -> int:
    if member.file_size > max_bytes: raise ValueError("ZIP member exceeds the configured uncompressed-size limit")
    written=0
    with archive.open(member) as source, destination.open("wb") as target:
        while True:
            chunk=source.read(1024 * 1024)
            if not chunk: break
            written += len(chunk)
            if written > max_bytes: raise ValueError("ZIP member exceeds the configured uncompressed-size limit")
            target.write(chunk)
    return written

def _discover_archive(path: Path, max_files: int, max_bytes: int, temporary_archives: list[Path], counter: list[int]) -> list[SourceSpec]:
    sources=[]
    try:
        archive=zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid ZIP archive: {path.name}") from exc
    with archive:
        for member in archive.infolist():
            if member.is_dir(): continue
            _safe_member_name(member.filename)
            counter[0] += member.file_size
            if counter[0] > max_bytes: raise ValueError("ZIP input exceeds the configured uncompressed-size limit")
            if member.filename.lower().endswith(".pdf"):
                sources.append(SourceSpec("zip",path,member.filename,f"{path.name}::{member.filename}"))
                if len(sources) > max_files: raise ValueError(f"Batch exceeds the configured limit of {max_files} PDFs")
            elif member.filename.lower().endswith(".zip"):
                fd,nested_name=tempfile.mkstemp(prefix="invoiceflow-nested-",suffix=".zip"); os.close(fd); nested=Path(nested_name); temporary_archives.append(nested)
                _copy_member(archive,member,nested,max_bytes)
                nested_sources=_discover_archive(nested,max_files-len(sources),max_bytes,temporary_archives,counter)
                sources.extend(nested_sources)
                if len(sources) > max_files: raise ValueError(f"Batch exceeds the configured limit of {max_files} PDFs")
    return sources

def discover_inputs(paths: Iterable[str | Path], max_files: int = DEFAULT_MAX_FILES, max_bytes: int = DEFAULT_MAX_BYTES) -> Discovery:
    sources=[]; temporary=[]; counter=[0]
    for raw in paths:
        path=Path(raw)
        if path.suffix.lower()==".pdf":
            sources.append(SourceSpec("file",path,display_name=path.name))
        elif path.suffix.lower()==".zip":
            sources.extend(_discover_archive(path,max_files-len(sources),max_bytes,temporary,counter))
        if len(sources)>max_files: raise ValueError(f"Batch exceeds the configured limit of {max_files} PDFs")
    return Discovery(sorted(sources,key=lambda item:item.display_name.casefold()),temporary,counter[0])

def safe_zip_extract(zip_path: str | Path, output_dir: str | Path, max_files: int = DEFAULT_MAX_FILES, max_bytes: int = DEFAULT_MAX_BYTES) -> list[Path]:
    """Compatibility helper; production processing uses discover_inputs and streams entries."""
    output_dir=Path(output_dir).resolve(); output_dir.mkdir(parents=True,exist_ok=True); discovery=discover_inputs([zip_path],max_files,max_bytes); paths=[]
    try:
        for index,spec in enumerate(discovery.sources):
            target=output_dir / f"{index:05d}_{Path(spec.member).name if spec.member else spec.path.name}"
            if spec.kind=="file": shutil.copyfile(spec.path,target)
            else:
                with zipfile.ZipFile(spec.path) as archive: _copy_member(archive,archive.getinfo(spec.member),target,max_bytes)
            paths.append(target)
        return paths
    finally:
        for path in discovery.temporary_archives:
            path.unlink(missing_ok=True)

def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()

def _materialize(spec: SourceSpec, temp_dir: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> tuple[Path,str]:
    if spec.kind=="file": return spec.path,_sha256(spec.path)
    path=temp_dir / (hashlib.sha1(spec.display_name.encode()).hexdigest()+".pdf")
    with zipfile.ZipFile(spec.path) as archive: _copy_member(archive,archive.getinfo(spec.member),path,max_bytes)
    return path,_sha256(path)

def _process_one(spec: SourceSpec, max_bytes: int = DEFAULT_MAX_BYTES) -> InvoiceRecord:
    with tempfile.TemporaryDirectory(prefix="invoiceflow-pdf-") as temp:
        try:
            path,digest=_materialize(spec,Path(temp),max_bytes); record=parse_invoice(extract_pdf(path)); record.source_sha256=digest; record.source_file=spec.display_name or str(spec.path); return record
        except Exception as exc:
            record=InvoiceRecord(source_file=spec.display_name or str(spec.path),status=ProcessingStatus.ERROR)
            record.issues.append(ValidationIssue("PROCESSING_ERROR",str(exc),"error")); return record

def process_batch(paths: Iterable[str | Path], callback: Callable[[int,int,str],None] | None=None, max_files: int=DEFAULT_MAX_FILES, max_bytes: int=DEFAULT_MAX_BYTES, workers: int=2, cancel_event: threading.Event | None=None, result_callback: Callable[[InvoiceRecord],None] | None=None, state_path: str | Path | None=None, job_id: str="default", resume: bool=False) -> list[InvoiceRecord]:
    discovery=discover_inputs(paths,max_files,max_bytes); state_store=JobStore(Path(state_path).parent) if state_path else None; state=(state_store.load(job_id) if state_store and resume else None) or JobState(job_id,total=len(discovery.sources)); completed_sources=set(state.completed_sources or []) if state else set(); specs=[spec for spec in discovery.sources if spec.display_name not in completed_sources]; total=len(discovery.sources); records=[]; seen_hashes=set(); completed=state.completed if state else 0
    try:
        with ThreadPoolExecutor(max_workers=max(1,min(workers,4)),thread_name_prefix="invoiceflow") as executor:
            pending: dict[Future[InvoiceRecord],SourceSpec]={}; source_iter=iter(specs)
            def fill() -> None:
                while len(pending)<max(1,min(workers,4)) and not (cancel_event and cancel_event.is_set()):
                    try: spec=next(source_iter)
                    except StopIteration: break
                    pending[executor.submit(_process_one,spec,max_bytes)]=spec
            fill()
            while pending:
                done,_=wait(tuple(pending),return_when=FIRST_COMPLETED)
                for future in done:
                    spec=pending.pop(future); record=future.result(); completed+=1
                    if record.source_sha256 and record.source_sha256 in seen_hashes:
                        record.duplicate_status="EXACT_DUPLICATE"; record.status=ProcessingStatus.NEEDS_REVIEW; record.issues.append(ValidationIssue("EXACT_DUPLICATE","The same PDF bytes appeared more than once in this batch.","warning","source_file"))
                    elif record.source_sha256: seen_hashes.add(record.source_sha256)
                    records.append(record)
                    if state_store:
                        state.completed=completed; state.completed_sources.append(spec.display_name); state.failed += int(record.status==ProcessingStatus.ERROR); state.cancelled=bool(cancel_event and cancel_event.is_set()); state_store.save(state)
                    if result_callback: result_callback(record)
                    if callback: callback(completed,total,Path(record.source_file).name)
                fill()
        records.sort(key=lambda item:item.source_file.casefold()); detect_duplicates(records)
        if state_store and not (cancel_event and cancel_event.is_set()): state_store.clear(job_id)
        return records
    finally:
        for path in discovery.temporary_archives: path.unlink(missing_ok=True)

def retry_failed(records: Iterable[InvoiceRecord], callback: Callable[[int,int,str],None] | None=None) -> list[InvoiceRecord]:
    paths=[record.source_file for record in records if record.status==ProcessingStatus.ERROR and Path(record.source_file).suffix.lower()==".pdf"]
    return process_batch(paths,callback=callback,max_files=max(DEFAULT_MAX_FILES,len(paths))) if paths else []
