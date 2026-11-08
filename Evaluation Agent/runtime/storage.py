"""Read source records without modifying them; append durable evaluation records."""

from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from runtime import portable_json as json
import os
from pathlib import Path

from runtime.paths import relocated_path
from runtime.agent import canonical_hash, parse_json, validate_source, record_format as _record_format


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_sources(batch_dir, source_model=None, source_files=None):
    batch_dir = relocated_path(batch_dir)
    if source_files is None and not batch_dir.is_dir():
        raise ValueError(f"Source batch does not exist: {batch_dir}")
    if source_files is not None:
        files = [relocated_path(file).resolve() for file in source_files]
    elif source_model is None:
        files = sorted(batch_dir.glob("responses_*.jsonl"))
    else:
        files = [batch_dir / f"responses_{source_model}.jsonl"]
    if not files or any(not file.is_file() for file in files):
        raise ValueError("No matching responses_<model>.jsonl input files were found.")
    queues = {}
    issues = []
    seen_ids = set()
    for path in files:
        decoder = _record_format.RecordDecoder()
        with path.open(encoding="utf-8-sig") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                source = {"source_file": str(path.resolve()), "source_line": line_number}
                try:
                    record = decoder.decode(parse_json(line))
                    if record is None:  # The compact header is context, not an answer.
                        continue
                    validate_source(record)
                except _record_format.HeaderError as exc:
                    raise ValueError(f"Invalid source header in {path}, line {line_number}: {exc}") from exc
                except (ValueError, TypeError) as exc:
                    source.update(status="input_error", error_type=type(exc).__name__, error=str(exc))
                    issues.append(source)
                    continue
                response_id = record["response_id"]
                if response_id in seen_ids:
                    raise ValueError(f"Duplicate response_id in source files: {response_id}; inspect inputs before evaluating.")
                seen_ids.add(response_id)
                source.update(record=record, source_sha256=canonical_hash(record))
                # First ten selected rows cover both models across all five scenarios.
                key = (str(record.get("scenario_id", "")), path.name)
                queues.setdefault(key, deque()).append(source)
    ordered = []
    keys = sorted(queues)
    while any(queues.values()):
        for key in keys:
            if queues[key]:
                ordered.append(queues[key].popleft())
    return ordered, issues


def check_log_boundary(path):
    if path.exists() and path.stat().st_size:
        with path.open("rb") as stream:
            stream.seek(-1, 2)
            if stream.read(1) != b"\n":
                raise ValueError(f"Log has an incomplete final line: {path}. Inspect it before continuing; nothing was removed.")


def append_record(path, record):
    check_log_boundary(path)
    serialized = json.dumps(record, ensure_ascii=False, allow_nan=False)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized + "\n")
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def evaluation_session(folder, rubric_path, rubric_hash, manifest, *,
                       checklist_path=None, checklist_hash=None, checklist_text=None,
                       calibration_path=None, calibration_hash=None):
    # A new round must never append to or overwrite an existing round folder.
    folder.mkdir(parents=True, exist_ok=False)
    lock = folder / ".run.lock"
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError(f"Another evaluation may be running. Inspect {lock} before restarting; remove a stale lock only after the previous process has stopped.") from exc
    try:
        with handle:
            handle.write(json.dumps({"pid": os.getpid(), "started_at_utc": utc_now()}))
        snapshot = folder / "rubric.md"
        raw = rubric_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != rubric_hash:
            raise ValueError("Rubric changed while preparing the run. Restart to use one consistent version.")
        if snapshot.exists() and snapshot.read_bytes() != raw:
            raise ValueError("Saved rubric snapshot differs; inspect the evaluation folder.")
        if not snapshot.exists():
            snapshot.write_bytes(raw)
        if checklist_text is not None:
            if checklist_path is not None:
                raise ValueError("Provide an integrated checklist or an external checklist, not both.")
            checklist_raw = checklist_text.encode("utf-8")
            if hashlib.sha256(checklist_raw).hexdigest() != checklist_hash:
                raise ValueError("Integrated checklist hash does not match its text.")
            (folder / "checklist.md").write_bytes(checklist_raw)
        if checklist_path is not None:
            checklist_raw = checklist_path.read_bytes()
            if hashlib.sha256(checklist_raw).hexdigest() != checklist_hash:
                raise ValueError("Checklist changed while preparing the run. Restart to use one consistent version.")
            (folder / "checklist.md").write_bytes(checklist_raw)
        if calibration_path is not None:
            calibration_raw = Path(calibration_path).read_bytes()
            if hashlib.sha256(calibration_raw).hexdigest() != calibration_hash:
                raise ValueError("Human calibration reference changed while preparing the run.")
            (folder / "calibration.md").write_bytes(calibration_raw)
        manifest_path = folder / "manifest.json"
        if manifest_path.exists():
            if parse_json(manifest_path.read_text(encoding="utf-8")) != manifest:
                raise ValueError("Evaluation manifest differs; inspect the output folder.")
        else:
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name in ("evaluations.jsonl", "errors.jsonl", "needs_review.jsonl"):
            check_log_boundary(folder / name)
        yield
    finally:
        lock.unlink()
