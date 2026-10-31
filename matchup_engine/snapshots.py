"""Immutable-style prediction snapshots for prospective accountability.

Snapshots are written once; reruns refuse to overwrite the same snapshot.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import pandas as pd

def save_prediction_snapshot(board, output_dir, as_of, generated_at=None):
    if board.empty:
        raise ValueError("Cannot snapshot an empty board")
    stamp=pd.Timestamp(generated_at or datetime.now(timezone.utc))
    if stamp.tzinfo is None:
        stamp=stamp.tz_localize("UTC")
    else:
        stamp=stamp.tz_convert("UTC")
    directory=Path(output_dir)
    directory.mkdir(parents=True,exist_ok=True)
    label=stamp.strftime("%Y%m%dT%H%M%S%fZ")
    path=directory/f"predictions_{label}.csv"
    metadata=directory/f"predictions_{label}.json"
    if path.exists() or metadata.exists():
        raise FileExistsError("Prediction snapshot already exists")
    payload=board.sort_values("game_id").to_csv(index=False).encode()
    digest=hashlib.sha256(payload).hexdigest()
    with path.open("xb") as f:
        f.write(payload)
    details={"generated_at_utc":stamp.isoformat(),"as_of":str(as_of),
             "games":len(board),"sha256":digest,
             "model_status":"PRELIMINARY_BASELINE"}
    with metadata.open("x",encoding="utf-8") as f:
        json.dump(details,f,indent=2)
    return path,metadata
