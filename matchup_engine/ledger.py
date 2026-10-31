"""Append-only prospective grading ledger with duplicate and integrity gates."""
from pathlib import Path
import hashlib
import json
import pandas as pd

def append_grading_ledger(graded, metrics, ledger_dir, snapshot_sha256):
    if not isinstance(snapshot_sha256,str) or len(snapshot_sha256)!=64:
        raise ValueError("A SHA-256 snapshot identifier is required")
    folder=Path(ledger_dir)
    folder.mkdir(parents=True,exist_ok=True)
    manifest=folder/"manifest.jsonl"
    existing=[]
    if manifest.exists():
        existing=[json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    if any(entry["snapshot_sha256"]==snapshot_sha256 for entry in existing):
        raise ValueError("Snapshot already recorded in grading ledger")
    record=graded.sort_values("game_id").to_csv(index=False).encode()
    grade_digest=hashlib.sha256(record).hexdigest()
    filename=f"grades_{snapshot_sha256[:16]}_{grade_digest[:16]}.csv"
    destination=folder/filename
    if destination.exists():
        raise FileExistsError("Grade file already exists")
    with destination.open("xb") as handle:
        handle.write(record)
    entry={"snapshot_sha256":snapshot_sha256,"grades_sha256":grade_digest,
           "grades_file":filename,"metrics":metrics}
    with manifest.open("a",encoding="utf-8") as handle:
        handle.write(json.dumps(entry,sort_keys=True)+"\n")
    return entry

def verify_grading_ledger(ledger_dir):
    folder=Path(ledger_dir)
    manifest=folder/"manifest.jsonl"
    if not manifest.exists():
        return {"entries":0,"verified":True}
    entries=[json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    ids=set()
    for entry in entries:
        if entry["snapshot_sha256"] in ids:
            raise ValueError("Duplicate snapshot in ledger")
        ids.add(entry["snapshot_sha256"])
        path=folder/entry["grades_file"]
        if not path.is_file():
            raise ValueError("Missing ledger grade file")
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry["grades_sha256"]:
            raise ValueError("Ledger grade file failed integrity verification")
    return {"entries":len(entries),"verified":True}
